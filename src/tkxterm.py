from queue import Queue
import atexit
import re
import os
import subprocess
from tkinter import ttk

from .command import Command, Callable
from .misc import string_normalizer, re_normalizer, base36encode


class Terminal(ttk.Frame):
    def __init__(self, 
            master = None,
            restore_on_close: bool = True,
            read_interval_ms: int = 100,
            read_length: int = 4096,
            **kwargs
        ):
        super().__init__(master, **kwargs)

        self._screen_name: str = f'tkxterm_{self.winfo_id()}'
        self._ready: bool = False
        self._before_init_queue: Queue[str] = Queue()
        self._next_id: int = 0
        self._command_dict: dict[int, Command] = {}
        self._xterm_proc: subprocess.Popen | None = None
        self._fifo_path: str = f"/tmp/{self._screen_name}.log"
        self._fifo_fd: int | None = None
        self._read_interval_ms: int = 0
        self._read_length: int = 0
        self._previous_readed: str = b''
        end_string: str = '\nID:{id};ExitCode:$?\n'
        self._end_string: str = string_normalizer(end_string)
        self._end_string_pattern: bytes = (re_normalizer(end_string)
            .replace(b'\\{id\\}', b'([0-9a-z]+)')
            .replace(b'\\$\\?', b'([0-9]{1,3})')
        )
        self._start_term_event: str | None = None
        self._read_fifo_event: str | None = None

        self.restore_on_close: bool = restore_on_close
        self.read_interval_ms = read_interval_ms
        self.read_length = read_length

        self.restart_term()

    @property
    def read_interval_ms(self) -> int:
        return self._read_interval_ms
    @read_interval_ms.setter
    def read_interval_ms(self, value: int) -> None:
        if isinstance(value, int):
            self._read_interval_ms = value
        else:
            raise TypeError('"read_interval_ms" not a "int" instance')
        
    @property
    def read_length(self) -> int:
        return self._read_length
    @read_length.setter
    def read_length(self, value: int) -> None:
        if isinstance(value, int):
            if value >= 1024:
                self._read_length = value
            else:
                raise ValueError('"read_length" smaller than 1kb')
        else:
            raise TypeError('"read_length" not a "int" instance')
    
    @property
    def ready(self) -> bool:
        return self._ready
    
    @property
    def end_string(self) -> bool:
        return self._end_string
    
    def restart_term(self, event=None):
        if self.winfo_ismapped():
            atexit.unregister(self._cleanup)
            atexit.register(self._cleanup)
            if not os.path.exists(self._fifo_path):
                os.mkfifo(self._fifo_path)
            if self._xterm_proc is None or self._xterm_proc.poll() is not None:
                self._xterm_proc = subprocess.Popen(
                    f"xterm -into {self.winfo_id()} -geometry 1000x1000 -e '" + string_normalizer(
                        f"if (screen -ls | grep {self._screen_name}); then "
                            f"screen -r {self._screen_name}; "
                        f"else "
                            f"screen -S {self._screen_name} -L -Logfile {self._fifo_path}; "
                        f"fi"
                    ) + f"'",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            if self._fifo_fd is None:
                self._fifo_fd = os.open(self._fifo_path, os.O_RDONLY | os.O_NONBLOCK)
            if self._read_fifo_event is None:
                self._read_fifo_event = self.after(self._read_interval_ms, self._read_fifo)
            if self._start_term_event is not None:
                self._start_term_event = self.unbind("<Visibility>", self._start_term_event)

        elif self._start_term_event is None:
            self._start_term_event = self.bind("<Visibility>", self.restart_term, '+')

    def _read_fifo(self):
        try:
            readed = os.read(self._fifo_fd, self._read_length)
            if not readed and self._ready:
                self._ready = False
                self.event_generate('<<TerminalClosed>>')
                if self.restore_on_close:
                    self.restart_term()
        except BlockingIOError:
            readed = b''

        union = self._previous_readed + readed
        mid_index = len(self._previous_readed)

        if readed:
            if not self._ready:
                self._ready = True
                self.event_generate('<<TerminalReady>>')
                while not self._before_init_queue.empty():
                    self.send_string(self._before_init_queue.get())
            else:
                match_iter = re.finditer(self._end_string_pattern, union)
                for match in match_iter:
                    key_id = int(match.group(1), base=36)
                    command = self._command_dict.get(key_id)
                    if command is not None:
                        command.exit_code = int(match.group(2))
                        self._command_dict.pop(key_id)
                        self.event_generate('<<CommandEnded>>', data=command)
                        mid_index = match.end()

        self._previous_readed = union[mid_index:]
        self._read_fifo_event = self.after(self._read_interval_ms, self._read_fifo)

    def run_command(self, cmd: str, background: bool = False, callback: Callable | None = None) -> Command:
        end_command = f'printf "{self._end_string.format(id=base36encode(self._next_id))}"'
        cmd = cmd.strip()
        cmd_string = f"({cmd}); {end_command}"
        if background:
            cmd_string = f"({cmd_string}) &"
        self.send_string(f'{cmd_string}\n')

        command = Command(cmd, callback)
        self._command_dict[self._next_id] = command
        self._next_id += 1
        return command

    def send_string(self, string: str) -> None:
        if self._ready:
            string = string_normalizer(string).replace("$", "\\$")
            subprocess.Popen(
                f"screen -S {self._screen_name} -X stuff '{string}'",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).wait()
            self.event_generate('<<StringSent>>', data=string)
        else:
            self._before_init_queue.put(string)

    def destroy(self):
        self._cleanup()
        super().destroy()

    def _cleanup(self):
        subprocess.Popen(
            f'screen -ls | grep {self._screen_name} | cut -f 2 | while read line; do screen -S $line -X quit ; done',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).wait()
        if self._start_term_event is not None:
            self._start_term_event = self.unbind("<Visibility>", self._start_term_event)
        if self._read_fifo_event is not None:
            self._read_fifo_event = self.after_cancel(self._read_fifo_event)
        if self._fifo_fd is not None:
            self._fifo_fd = os.close(self._fifo_fd)
        if self._xterm_proc is not None:
            self._xterm_proc = self._xterm_proc.terminate()
        if os.path.exists(self._fifo_path):
            os.remove(self._fifo_path)
        atexit.unregister(self._cleanup)
