from queue import Queue
import atexit
import re
import os
import subprocess
from tkinter import ttk

from .command import Command, Callable
from .misc import string_normalizer, re_normalizer, base36encode


class Terminal(ttk.Frame):
    def __init__(self, master = None, **kwargs):
        super().__init__(master, **kwargs)

        self.screen_name: str = f'tkxterm_{self.winfo_id()}'
        self.is_initialized: bool = False
        self.before_init_queue: Queue[str] = Queue()
        self.next_id: int = 0
        self.command_dict: dict[int, Command] = {}

        self.fifo_path: str = f"/tmp/{self.screen_name}.log"
        self.fifo_fd: int | None = None
        self.read_interval_ms: int = 100
        self.read_lenght: int = 4096
        self.previous_readed: str = b''
        end_string: str = '\nID:{id};ExitCode:$?\n'
        self.end_string: str = string_normalizer(end_string)
        self.end_string_pattern: bytes = (re_normalizer(end_string)
            .replace(b'\{id\}', b'([0-9a-z]+)')
            .replace(b'\$\?', b'([0-9]{1,3})')
        )

        self.start_term_event: str | None = self.bind("<Visibility>", self.restart_term, '+')
        self.read_fifo_event: str | None = None

    def restart_term(self, event=None):
        if self.winfo_exists():
            atexit.unregister(self.cleanup)
            atexit.register(self.cleanup)
            if not os.path.exists(self.fifo_path):
                os.mkfifo(self.fifo_path)
            subprocess.Popen(
                f"xterm -into {self.winfo_id()} -geometry 1000x1000 -e '" + string_normalizer(
                    f"if (screen -ls | grep {self.screen_name}); then "
                        f"screen -r {self.screen_name} || (screen -S {self.screen_name} -X quit; screen -S {self.screen_name} -L -Logfile {self.fifo_path}); "
                    f"else "
                        f"screen -S {self.screen_name} -L -Logfile {self.fifo_path}; "
                    f"fi"
                ) + f"'",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if self.fifo_fd is None:
                self.fifo_fd = os.open(self.fifo_path, os.O_RDONLY | os.O_NONBLOCK)
            if self.read_fifo_event is None:
                self.read_fifo_event = self.after(self.read_interval_ms, self.read_fifo)
            if self.start_term_event is not None:
                self.unbind("<Visibility>", self.start_term_event)
                self.start_term_event = None

    def read_fifo(self):
        try:
            readed = os.read(self.fifo_fd, self.read_lenght)
        except BlockingIOError:
            readed = b''

        union = self.previous_readed + readed
        mid_index = len(self.previous_readed)

        if readed:
            if not self.is_initialized:
                self.is_initialized = True
                self.event_generate('<<TerminalInitialized>>')
                while not self.before_init_queue.empty():
                    self.send_string(self.before_init_queue.get())
            else:
                match_iter = re.finditer(self.end_string_pattern, union)
                for match in match_iter:
                    command = self.command_dict.get(int(match.group(1), base=36))
                    if command is not None and command.exit_code is None:
                        command.exit_code = int(match.group(2))
                        self.event_generate('<<CommandEnded>>', data=command)
                        mid_index = match.end()

        self.previous_readed = union[mid_index:]
        self.read_fifo_event = self.after(self.read_interval_ms, self.read_fifo)

    def run_command(self, cmd: str, background: bool = False, callback: Callable | None = None) -> Command:
        end_command = f'printf "{self.end_string.format(id=base36encode(self.next_id))}"'
        cmd = cmd.strip()
        cmd_string = f"({cmd}); {end_command}"
        if background:
            cmd_string = f"({cmd_string}) &"
        self.send_string(f'{cmd_string}\n')

        command = Command(cmd, callback)
        self.command_dict[self.next_id] = command
        self.next_id += 1
        return command

    def send_string(self, string: str) -> None:
        if self.is_initialized:
            string = string_normalizer(string)
            string = string.replace("$", "\\$")
            subprocess.Popen(
                f"screen -S {self.screen_name} -X stuff '{string}'",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).wait()
            self.event_generate('<<StringSent>>', data=string)
        else:
            self.before_init_queue.put(string)

    def destroy(self):
        self.cleanup()
        super().destroy()

    def cleanup(self):
        subprocess.Popen(
            f'screen -ls | grep {self.screen_name} | cut -f 2 | while read line; do screen -S $line -X quit ; done',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if self.read_fifo_event is not None:
            self.after_cancel(self.read_fifo_event)
            self.read_fifo_event = None
        if self.fifo_fd is not None:
            os.close(self.fifo_fd)
            self.fifo_fd = None
        if os.path.exists(self.fifo_path):
            os.remove(self.fifo_path)
        atexit.unregister(self.cleanup)
