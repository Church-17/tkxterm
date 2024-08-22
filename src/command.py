class Command:
    def __init__(self, cmd: str):
        self.cmd = cmd
        self.output = None
        self.exit_code = None
