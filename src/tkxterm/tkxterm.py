from typing import Callable
from queue import Queue
import atexit
import re
import os
import subprocess
import tkinter as tk
from tkinter import ttk

from ._parser import string_normalizer, re_normalizer, base36encode
from .command import Command


class Terminal(ttk.Frame):
    "XTerm frame in Tkinter"

    def __init__(self, 
            master = None,
            restore_on_close: bool = True,
            read_interval_ms: int = 100,
            read_length: int = 4096,
            **kwargs
        ) -> None:
        """
        Create a Ttk frame with XTerm embedded. All the Ttk Frame options are available.
        
        Parameters:
        - `restore_on_close: bool` If XTerm is closed (e.g. by a Ctrl-D), it will restart automatically;
        - `read_interval_ms: int` Interval in ms for reading the terminal to capture the exit codes;
        - `read_length: int` How many bytes are readed per interval at most;
        """

        # Create Ttk frame
        super().__init__(master, **kwargs)

        # Interval variables
        self._screen_name: str = f'tkxterm_{self.winfo_id()}'
        self._ready: bool = False
        self._before_init_queue: Queue[str] = Queue()
        self._next_id: int = 0
        self._command_dict: dict[int, Command] = {}
        self._xterm_proc: subprocess.Popen | None = None

        # Variables for read fifo
        self._fifo_path: str = f'/tmp/{self._screen_name}.log'
        self._fifo_fd: int | None = None
        self._previous_readed: bytes = b''
        end_string: str = '\nID:{id};ExitCode:$?\n'
        self._end_string: str = string_normalizer(end_string).replace("\"", "\\\"")
        self._end_string_pattern: bytes = (re_normalizer(end_string)
            .replace(b'\\{id\\}', b'([0-9a-z]+)')
            .replace(b'\\$\\?', b'([0-9]{1,3})')
        )

        # Event identifiers
        self._restart_term_event: str | None = None
        self._read_fifo_event: str | None = None

        # Initialize properties
        self._read_interval_ms: int = 0
        self._read_length: int = 0
        self.restore_on_close: bool = restore_on_close
        self.read_interval_ms = read_interval_ms
        self.read_length = read_length

        # Start terminal
        self.restart_term()

    @property
    def read_interval_ms(self) -> int:
        return self._read_interval_ms
    
    @read_interval_ms.setter
    def read_interval_ms(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError('"read_interval_ms" not a "int" instance')
        self._read_interval_ms = value
        
    @property
    def read_length(self) -> int:
        return self._read_length
    
    @read_length.setter
    def read_length(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError('"read_length" not a "int" instance')
        if value < 1024:
            raise ValueError('"read_length" smaller than 1kb')
        self._read_length = value
    
    @property
    def ready(self) -> bool:
        return self._ready
    
    @property
    def end_string(self) -> str:
        return self._end_string
    
    def restart_term(self, _: tk.Event | None = None) -> None:
        """Procedure to restart XTerm"""

        # If this frame is visible...
        if self.winfo_ismapped():

            # Ensure one cleanup on exit
            atexit.unregister(self._cleanup)
            atexit.register(self._cleanup)

            # If fifo not exist create it
            if not os.path.exists(self._fifo_path):
                os.mkfifo(self._fifo_path)
            
            # If XTerm process is off create it
            if self._xterm_proc is None or self._xterm_proc.poll() is not None:
                self._xterm_proc = subprocess.Popen(
                    # Start XTerm in frame (geometry will adapt)
                    f"xterm -into {self.winfo_id()} -geometry 1000x1000 -e \'" + string_normalizer(
                        # If the screen exists recover it, else create it
                        f"if (screen -ls | grep \"{self._screen_name}\"); then "
                            f"screen -r \"{self._screen_name}\"; "
                        f"else "
                            f"screen -S \"{self._screen_name}\" -L -Logfile \"{self._fifo_path}\"; "
                        f"fi"
                    ) + f"\'",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            
            # If fifo is not opened, open it
            if self._fifo_fd is None:
                self._fifo_fd = os.open(self._fifo_path, os.O_RDONLY | os.O_NONBLOCK)

            # Plan reading fifo
            if self._read_fifo_event is None:
                self._read_fifo_event = self.after(self._read_interval_ms, self._read_fifo)
            
            # Remove the planned restart_term procedure once it's been executed if it was planned
            if self._restart_term_event is not None:
                self._restart_term_event = self.unbind("<Visibility>", self._restart_term_event)

        # Plan the restart_term procedure if this frame is not visible and if it's not been done yet
        elif self._restart_term_event is None:
            self._restart_term_event = self.bind("<Visibility>", self.restart_term, '+')

    def _read_fifo(self) -> None:
        """Read the fifo screen log"""

        # Read fifo
        # It returns an empty bytes if no writer have opened it
        # It raise BlockingIOError if writer have opened it but it doesn't write anything
        try:
            readed = os.read(self._fifo_fd, self._read_length)
        except BlockingIOError:
            readed = None

        # If terminal is not ready but a writer connect to the fifo...
        if not self._ready and readed != b'':
            # Set logfile flush to 0
            subprocess.Popen(
                f"screen -S {self._screen_name} -X logfile flush 0",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).wait()

            # Set ready state
            self._ready = True
            self.event_generate('<<TerminalReady>>')

            # Send to terminal all elements in queue
            while not self._before_init_queue.empty():
                self.send_string(self._before_init_queue.get())
            
        # If terminal is ready but the writer disconnect from the fifo...
        elif self._ready and readed == b'':
            # Set ready state
            self._ready = False
            self.event_generate('<<TerminalClosed>>')

            # Restart terminal if needed
            if self.restore_on_close:
                self.restart_term()

        # Make readed coherent bytes
        if readed is None:
            readed = b''

        # Search in union of previous_readed and readed, to handle broken regex
        union = self._previous_readed + readed
        mid_index = len(self._previous_readed)

        # If it has readed something
        if readed:
            match_iter = re.finditer(self._end_string_pattern, union)
            for match in match_iter:
                # Get Command instance by ID (regex group 1)
                key_id = int(match.group(1), base=36)
                command = self._command_dict.get(key_id, None)
                if command is not None:
                    # Set exit code
                    command.exit_code = int(match.group(2))
                    self._command_dict.pop(key_id)
                    self.event_generate('<<CommandEnded>>', data=command)
                    # Found a match, so before there can't be broken regex
                    mid_index = match.end()

        # Update previous readed
        self._previous_readed = union[mid_index:]

        # Plan next reading
        self._read_fifo_event = self.after(self._read_interval_ms, self._read_fifo)

    def run_command(self, cmd: str, background: bool = False, callback: Callable[[Command], object] | None = None) -> Command:
        """
        Send a command to the terminal. It returns a Command object.
        
        Use `background` to execute it in background, because using simply `&` the exit code indicates only if the command started correctly or not.
        
        Set `callback` to a function you want to execute at the finish of the command. It receives the Command object as a parameter.
        """

        # Check params
        if not isinstance(cmd, str):
            cmd = str(cmd)

        # Create command string, adding end command
        cmd = cmd.strip()
        cmd_string = f"({cmd}); printf \"{self.end_string.format(id=base36encode(self._next_id))}\""

        # Add '&' if backgrounf is on
        if background:
            cmd_string = f"({cmd_string}) &"

        # Send command to terminal
        self.send_string(f'{cmd_string}\n')

        # Create Command object with unique ID
        command = Command(cmd, callback)
        self._command_dict[self._next_id] = command
        self._next_id += 1

        return command

    def send_string(self, string: str) -> None:
        """Send a string to the terminal"""

        # If the terminal is ready, send the string
        if self._ready:
            string = string_normalizer(string).replace("$", "\\$")
            subprocess.Popen(
                f"screen -S \"{self._screen_name}\" -X stuff \'{string}\'",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).wait()
            self.event_generate('<<StringSent>>', data=string)

        # If the terminal is not ready, save the string in a queue
        else:
            self._before_init_queue.put(string)

    # Override the destroy method to also cleanup
    def destroy(self) -> None:
        self._cleanup()
        super().destroy()

    def _cleanup(self) -> None:
        """Cleanup all the done"""
        
        # Close every possible instances of the screen with that name
        subprocess.Popen(
            f'screen -ls | grep \"{self._screen_name}\" | cut -f 2 | while read line; do screen -S \"$line\" -X quit ; done',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).wait()

        # Unplan the restart_term event is it is planned
        if self._restart_term_event is not None:
            self._restart_term_event = self.unbind("<Visibility>", self._restart_term_event)
        
        # Unplan to read the fifo if it is planned
        if self._read_fifo_event is not None:
            self._read_fifo_event = self.after_cancel(self._read_fifo_event)

        # Close the fifo file descriptor if it is opened
        if self._fifo_fd is not None:
            self._fifo_fd = os.close(self._fifo_fd)
        
        # Terminate XTerm if it is running
        if self._xterm_proc is not None:
            self._xterm_proc = self._xterm_proc.terminate()

        # Remove the fifo if it exists
        if os.path.exists(self._fifo_path):
            os.remove(self._fifo_path)

        # Unplan the cleanup procedure
        atexit.unregister(self._cleanup)
