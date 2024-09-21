from collections.abc import Callable


class Command:
    """Command with its result"""

    def __init__(self, cmd: str, callback: Callable | None = None) -> None:
        """
        Create a Command instance, with the command string, the exit code and a callback to execute when it finished
        """

        # Check params
        if not isinstance(cmd, str):
            raise TypeError("cmd must be a string")

        # Internal variables
        self._cmd: str = cmd
        self._exit_code: int | None = None
        
        # Set properties
        self.callback = callback

    @property
    def cmd(self) -> str:
        return self._cmd
    
    @property
    def exit_code(self) -> int | None:
        return self._exit_code
    
    @exit_code.setter
    def exit_code(self, value) -> None:
        # Set only one time the exit code, if it is valid
        if self._exit_code is None and isinstance(value, int) and 0 <= value < 256:
            self._exit_code = value

            # Execute callback if there is one
            if self.callback:
                self.callback(self)

    @property
    def callback(self) -> Callable | None:
        return self._callback

    @callback.setter
    def callback(self, func: Callable | None) -> None:
        if not isinstance(func, Callable | None):
            raise TypeError('"func" not a "Callable" instance')
        self._callback: Callable | None = func
