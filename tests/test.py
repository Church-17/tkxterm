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
window.columnconfigure(0, weight=1)
window.rowconfigure(0, weight=1)
window.focus_force()

notebook = ttk.Notebook(window)
notebook.grid(column=0, row=0, sticky='NSWE')

term0 = Terminal(notebook, restore_on_close=True)
term0.grid(column=0, row=0, sticky='NSWE')
notebook.add(term0)
term1 = Terminal(notebook)
term1.grid(column=0, row=0, sticky='NSWE')
notebook.add(term1)


res0 = term0.run_command('sleep 2;cd; ./a.sh', True,
    lambda x: print(f'EXITCODE OF {x.cmd} ({x}):', x.exit_code)
)
term0.run_command('echo ok', callback=lambda x: print(x.cmd, x.exit_code))

# window.after(5000, term0.restart_term)
window.after(4000, lambda: term0.run_command('echo ok', callback=lambda x: print('hey')))

window.after(1000, lambda: term0.run_command('sleep 2;cd; ./a.sh', background=True))
window.after(2000, lambda: term0.run_command('sleep 2;cd; ./a.sh'))

res1 = term1.run_command('echo aa')
window.after(4000, lambda: term1.run_command('sleep 2;cd; ./a.sh', callback=lambda x: print(x.exit_code)))
window.after(5000, lambda: term1.run_command("echo '4'"))
window.after(7000, lambda: term1.run_command("echo \"\nci\rao\n\""))
window.after(8000, lambda: term1.run_command("echo \"$PS1\""))

window.mainloop()

