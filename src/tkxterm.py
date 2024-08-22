from queue import Queue
import atexit
import re
import os
import subprocess
from tkinter import ttk

from .command import Command
from .misc import string_normalizer, re_normalizer


class Terminal(ttk.Frame):
    def __init__(self,
            master = None,
            end_string: str = '\nExitCode: $?\n',
            **kwargs
        ):
        super().__init__(master, **kwargs)

        self.screen_name: str = str(self.winfo_id())
        self.command_queue: Queue = Queue()
        self.fifo_path: str = f"/tmp/{self.screen_name}.log"
        self.fifo_fd: int | None = None
        self.cmd_found: bool | None = None
        self.previous_readed: str = b''
        self.partial_command_output: bytes = b''
        self.current_command: Command | None = None
        self.current_command_pattern: bytes = b''
        self.end_string: str = string_normalizer(end_string)
        self.end_string_pattern: bytes = re_normalizer(end_string).replace(b'\$\?', b'([0-9]{1,3})')
        self.start_term_event: str = self.bind("<Visibility>", self.start_term, '+')
        self.read_fifo_event: str | None = None

        self.log = b''

    def start_term(self, event):
        atexit.register(self.cleanup)
        subprocess.Popen(
            f"xterm -into {self.screen_name} -geometry 1000x1000 -e '" +
                string_normalizer(f"screen -S {self.screen_name} -L -Logfile {self.fifo_path}") +
            f"'",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        os.mkfifo(self.fifo_path)
        self.fifo_fd = os.open(self.fifo_path, os.O_RDONLY | os.O_NONBLOCK)
        self.read_fifo_event = self.after(100, self.read_fifo)
        self.unbind("<Visibility>", self.start_term_event)

    def read_fifo(self):
        try:
            readed = os.read(self.fifo_fd, 100)
            if readed:
                print("READ:", readed)
                union = self.previous_readed + readed
                print("UNION:", union)
                union = re.sub(b'\x1b[\[\(]+[\?=]?[0-9;]*[0-9a-zA-Z]+\r?', b'', union)
                print("FILTER:", union)

                mid_index = 0
                for p, u in zip(self.previous_readed, union):
                    if p == u:
                        mid_index += 1
                    else:
                        break

                if self.cmd_found is None:
                    self.send_next_command()
                elif self.current_command is not None:

                    if not self.cmd_found:
                        print("SEARCH_CMD:", union)
                        search_current_command = re.search(self.current_command_pattern, union)
                        if search_current_command is not None:
                            print("CMD:", search_current_command)
                            cmd_index = mid_index = search_current_command.end()
                            self.cmd_found = True
                        else:
                            cmd_index = None
                    else:
                        cmd_index = 0

                    if cmd_index is not None:
                        print("SEARCH_END:", union[cmd_index:])
                        search_end_string = re.search(self.end_string_pattern, union[cmd_index:])
                        if search_end_string is not None:
                            print("EC:", search_end_string.group(1))
                            self.current_command.output = self.partial_command_output + union[cmd_index:cmd_index+search_end_string.start()]
                            self.current_command.exit_code = int(search_end_string.group(1))
                            mid_index = search_end_string.end()
                            self.send_next_command()
                        elif cmd_index == 0:
                            self.partial_command_output += union[:mid_index]

                self.previous_readed = union[mid_index:]
                self.log += union[:mid_index]
                    

        except BlockingIOError:
            pass
        
        self.read_fifo_event = self.after(100, self.read_fifo)

    def send_next_command(self):
        self.partial_command_output = b''
        self.cmd_found = False
        if self.command_queue.empty():
            self.current_command, self.current_command_pattern = None, b''
        else:
            self.send_command(self.command_queue.get())

    def run_command(self, cmd: str) -> Command:
        command = Command(cmd)
        if self.current_command is not None or self.cmd_found is None:
            self.command_queue.put(command)
        else:
            self.send_command(command)
        return command

    def send_command(self, command: Command):
        self.current_command = command
        end_command = f'; printf "{self.end_string}"\n'
        cmd_pattern = command.cmd.replace('\n', '\n> ').replace('\r', '\r> ') + end_command
        cmd = command.cmd + end_command
        self.current_command_pattern = re_normalizer(cmd_pattern)
        self.send_string(cmd)

    def send_string(self, string: str) -> None:
        string = string_normalizer(string)
        string = string.replace("$", "\\$")
        subprocess.Popen(
            f"screen -S {self.screen_name} -X stuff '{string}'",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).wait()

    def destroy(self):
        self.cleanup()
        super().destroy()

    def cleanup(self):
        subprocess.Popen(
            f'screen -S {self.screen_name} -X quit',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if self.read_fifo_event is not None:
            self.after_cancel(self.read_fifo_event)
        if self.fifo_fd is not None:
            os.close(self.fifo_fd)
        if os.path.exists(self.fifo_path):
            os.remove(self.fifo_path)
        atexit.unregister(self.cleanup)
