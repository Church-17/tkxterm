# XTerm in Tkinter

This project is born with the purpose of having in a Tkinter GUI an embedded and fully functional bash terminal, to interact with and run some commands automatically viewing in real-time the results.

It's possible to send any commands to execute it, having back in the code an object that, after the end of the command, contains the exit code and can execute a callback.

For executing a command in background, there is a specific argument in the function rather than using the classic `&` method, because otherwise the command doesn't return its exit code, but if the command started correctly or not.
