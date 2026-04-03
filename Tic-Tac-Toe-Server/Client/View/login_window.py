import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

class LoginWindow:
    def __init__(self, controller, root):
        self.controller = controller
        self.root = root

        self.root = tk.Toplevel(root)
        self.root.protocol("WM_DELETE_WINDOW", self.controller.on_closing)
        self.root.title("Login / Register")
        self.window_width = 300
        self.window_height = 180

        self.frame = None
        self.username_entry = None
        self.password_entry = None
        self.combo_var = None
        self.combobox = None
        self.submit_button = None
        self.root.withdraw()


    def create_interface(self):
        self.root.deiconify()
        self.root.update_idletasks()
        self.center(self.root, self.window_width, self.window_height)
        self.root.configure(background="#EAF4F9")

        self.frame = tk.Frame(self.root, bg="#EAF4F9")
        self.frame.pack(padx=10, pady=10, fill="both", expand=True)

        tk.Label(self.frame, text="Username:", bg="#EAF4F9", fg="#243B4A").pack(anchor="w")
        self.username_entry = tk.Entry(self.frame, bg="#F5F9FC", fg="#243B4A", insertbackground="#243B4A")
        self.username_entry.pack(fill="x", pady=(0, 10))

        tk.Label(self.frame, text="Password:", bg="#EAF4F9", fg="#243B4A").pack(anchor="w")
        self.password_entry = tk.Entry(self.frame, show="*", bg="#F5F9FC", fg="#243B4A", insertbackground="#243B4A")
        self.password_entry.pack(fill="x", pady=(0, 10))

        self.combo_var = tk.StringVar()
        self.combobox = ttk.Combobox(
            self.frame,
            textvariable=self.combo_var,
            state="readonly",
            values=["login", "signup"],
            width=12
        )
        self.combobox.current(0)
        self.combobox.pack(pady=(0, 10))

        self.submit_button = tk.Button(
            self.frame,
            text="Submit",
            bg="#A0E9FF",
            fg="#243B4A",
            command=self.submit
        )
        self.submit_button.pack()


    @staticmethod
    def center(window, width, height):
        window.update_idletasks()
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")


    def submit(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        action = self.combo_var.get()
        print(f"{action} -> Username: {username}, Password: {password}")
        self.controller.verification(username, password, action)


    def disable_button(self):
        self.submit_button.configure(state="disabled")


    def enable_button(self):
        self.submit_button.configure(state="normal")


    def show_connection(self, message):
        if message.strip():
            messagebox.showinfo("Connection Status", message.strip(), parent=self.root)

    @staticmethod
    def show_verif_status(message):
        messagebox.showinfo("Verification status", message)



    def start(self):
        self.create_interface()
