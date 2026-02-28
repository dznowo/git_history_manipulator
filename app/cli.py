import tkinter as tk
from tkinter import filedialog, messagebox


class App:

    def __init__(self, root):
        self.root = root
        root.title("Git Time Rewriter")

        tk.Label(root, text="Выберите ветку").pack()
        self.branch_list = tk.Listbox(root, selectmode=tk.MULTIPLE)
        self.branch_list.pack(fill="both", expand=True)

        tk.Button(root, text="Dry Run", command=self.dry_run).pack()
        tk.Button(root, text="Apply", command=self.apply).pack()

    def dry_run(self):
        messagebox.showinfo("Preview", "Dry run выполнен")

    def apply(self):
        messagebox.showinfo("Apply", "История переписана")