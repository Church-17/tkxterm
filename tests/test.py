import sys
import tkinter as tk
from tkinter import ttk
sys.path.append('.')
from src.tkxterm import Terminal

TITLE = "Test"
SIZE_X = 800
SIZE_Y = 500

window = tk.Tk()
window.geometry(f'{SIZE_X}x{SIZE_Y}')
window.resizable(None, None)
window.minsize(SIZE_X, SIZE_Y)
window.maxsize(SIZE_X, SIZE_Y)
window.title(TITLE)
# window.columnconfigure(0, weight=1)
window.columnconfigure(1, weight=1)
window.rowconfigure(0, weight=1)
window.rowconfigure(1, weight=1)
window.focus_force()


# notebook = ttk.Notebook(window)
# notebook.grid(column=1, row=0, sticky='NSWE')

term0 = Terminal(window, restore_on_close=True)
term0.grid(row=0, column=1, sticky='NSWE', rowspan=2)

# notebook.add(term0)
# term1 = Terminal(notebook, restore_on_close=True)
# term1.grid(column=1, row=0, sticky='NSWE')

# notebook.add(term1)

frame0 = ttk.Frame(window)
frame0.grid(row=0, column=0)
frame0.columnconfigure(0, weight=1)
frame0.rowconfigure(0, weight=1)
frame0.rowconfigure(1, weight=1)

label0 = ttk.Label(frame0, text="")
label0.grid(row=1, column=0)

def command0():
    term0.run_command("echo Hello", callback=(lambda x: label0.configure(text=f"Exit code of \"{x.cmd}\": {x.exit_code}")))

but0 = ttk.Button(frame0, text='Send \"echo Hello\"', command=command0)
but0.grid(row=0, column=0)


frame1 = ttk.Frame(window)
frame1.grid(row=1, column=0)
frame1.columnconfigure(0, weight=1)
frame1.rowconfigure(0, weight=1)
frame1.rowconfigure(1, weight=1)

label1 = ttk.Label(frame1, text="")
label1.grid(row=1, column=0)

def command1():
    term0.run_command("invalid command", callback=(lambda x: label1.configure(text=f"Exit code of \"{x.cmd}\": {x.exit_code}")))

but1 = ttk.Button(frame1, text='Send invalid command', command=command1)
but1.grid(row=0, column=0)

window.mainloop()
