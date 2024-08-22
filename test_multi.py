import tkinter as tk
from tkinter import ttk

from src.tkxterm import Terminal

TITLE = "ZeuSys"
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

term0 = Terminal(notebook)
term0.grid(column=0, row=0, sticky='NSWE')
notebook.add(term0)
term1 = Terminal(notebook)
term1.grid(column=0, row=0, sticky='NSWE')
notebook.add(term1)

window.bind("<Control-Key-c>", lambda x: print('CTRL-C'))
res0 = term0.run_command('echo $PS1')
res0 = term0.run_command('sleep 3')
res1 = term1.run_command('echo aa')
window.after(4000, lambda: term1.run_command('sleep 3;cd; ./a.sh'))
window.after(5000, lambda: term1.run_command("echo '4'"))
window.after(5000, lambda: term1.send_string("ciao"))
window.after(5000, lambda: term1.run_command("echo \"\nci\rao\n\""))
window.after(5000, lambda: term1.run_command("echo \"$PS1\""))

window.after(500, lambda: print('OUT', res0.output, res0.exit_code))
window.after(10000, lambda: print(term0.log))
# window.after(3000, lambda: print(res1.output, res1.exit_code))

window.mainloop()

