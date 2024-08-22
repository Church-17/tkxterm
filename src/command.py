from typing import Callable

class Command:
    def __init__(self, cmd: str, callback: Callable | None = None) -> None:
        if not isinstance(cmd, str):
            raise TypeError('"cmd" not a "str" instance')

        self._cmd: str = cmd
        self._exit_code: int | None = None
        self._callback: Callable | None = None
        self.set_callback(callback)

    @property
    def cmd(self) -> str:
        return self._cmd
    
    @property
    def exit_code(self) -> int | None:
        return self._exit_code
    
    @exit_code.setter
    def exit_code(self, value) -> None:
        if self._exit_code is None and isinstance(value, int) and 0 <= value < 256:
            self._exit_code = value
            self.callback()

    def callback(self) -> None:
        if self._callback is not None:
            self._callback(self)

    def set_callback(self, func: Callable | None) -> None:
        if not isinstance(func, Callable | None):
            raise TypeError('"func" not a "Callable" instance')

        self._callback = func
        if self._exit_code is not None:
            self.callback()
