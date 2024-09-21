import sys
import tkinter as tk
from tkinter import ttk
sys.path.append('.')
from src.tkxterm import Terminal

TITLE = "Test"
SIZE_X = 1200
SIZE_Y = 700

window = tk.Tk()
window.geometry(f'{SIZE_X}x{SIZE_Y}')
window.resizable(None, None)
window.minsize(SIZE_X, SIZE_Y)
window.maxsize(SIZE_X, SIZE_Y)
window.title(TITLE)
window.columnconfigure(1, weight=1)
window.rowconfigure(0, weight=1)
window.focus_force()

term0 = Terminal(window, restore_on_close=True)
term0.grid(column=1, row=0, sticky='NSWE')

but = ttk.Button(window, text='ciao', command=(lambda: term0.run_command('echo ciao', callback=(lambda x: print('exit code di ciao: ', x.exit_code)))))
but.grid(row=0, column=0, sticky='w')

res0 = term0.run_command('sleep 2;cd; ./a.sh', True,
    lambda x: print(f'EXITCODE OF {x.cmd} ({x}):', x.exit_code)
)
term0.run_command(f'echo {"ok"*56}', callback=lambda x: print(x.cmd, x.exit_code))

window.after(4000, lambda: term0.run_command('echo ok', callback=lambda x: print('hey')))

window.after(1000, lambda: term0.run_command('sleep 2;cd; ./a.sh', background=True))

window.mainloop()

