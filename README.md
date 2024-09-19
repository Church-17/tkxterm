# TkXTerm - XTerm in Tkinter

[![PyPI](https://img.shields.io/pypi/v/tkxterm?style=flat)](https://pypi.python.org/pypi/tkxterm/)

TkXTerm makes available a Terminal Ttk frame, that have XTerm embedded and it can be used in the Tkinter GUI as a normal frame. It's possible to send any commands to execute it, having back in the code an object that, after the end of the command, contains the exit code and can execute a callback. It's also possible to use XTerm normally.

This project is born with the purpose of having an embedded and fully functional bash terminal in a Tkinter GUI, to interact with it and run some commands automatically, viewing in real-time the output and the results and having the exit code back into an object in the code.



To execute a command in background, there is a specific argument in the function rather than using the classic `&` method, because otherwise the exit code indicates only if the command started correctly or not, and not the actual exit code of the command runned in background.
