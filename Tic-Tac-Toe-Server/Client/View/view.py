import tkinter as tk
from tkinter import ttk
from tkinter import messagebox


class View:
    def __init__(self, controller, root):
        self.controller = controller
        self.root = root

        self.root = tk.Toplevel(root)
        self.root.title('Client')
        self.window_width =  400
        self.window_height = 550

        self.text_area = None
        self.bottom_frame = None
        self.entry = None
        self.combo_var = None
        self.send_button = None
        self.bottom_frame = None
        self.entry = None
        self.combobox = None

        self.root.withdraw()

    def create_main_interface(self):
        self.root.deiconify()

        self.root.update_idletasks()
        self.center(self.root, self.window_width, self.window_height)

        self.root.configure(background="#EAF4F9")

        self.text_area = tk.Text(self.root, state="disabled", wrap="word", bg="#BFDCEB", fg="DarkBlue", insertbackground="#1C2E3A")
        self.text_area.pack(padx=10, pady=10, fill="both", expand=True)

        self.bottom_frame = tk.Frame(self.root)
        self.bottom_frame.pack(fill="x", padx=10, pady=5)

        self.entry = tk.Entry(self.bottom_frame, bg="#F5F9FC", fg="#243B4A", insertbackground="#F5F9FC")
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.combo_var = tk.StringVar()

        self.combobox = ttk.Combobox(
            self.bottom_frame,
            textvariable=self.combo_var,
            state="readonly",
            values=["message", "image", "file"],
            width=12
        )
        self.combobox.current(0)
        self.combobox.pack(side="left", padx=(0, 5))

        self.send_button = tk.Button(self.bottom_frame, text="SEND MESSAGE", bg="#A0E9FF", fg="#243B4A", command=self.send_message)
        self.send_button.pack(side="right")

    @staticmethod
    def center(window, width, height):
        window.update_idletasks()
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")


    def send_message(self):
        message = self.entry.get()
        self.controller.send_message(message)
        self.show_my_message(message)


    def show_my_message(self, massage):
        if massage.strip():
            self.text_area.config(state="normal")
            self.text_area.insert(tk.END, f"Client: {massage}\n")
            self.text_area.config(state="disabled")
            self.text_area.see(tk.END)
            self.entry.delete(0, tk.END)


    def show_info(self, massage):
        if massage.strip():
            self.text_area.config(state="normal")
            self.text_area.insert(tk.END, f"{massage.upper()}\n")
            self.text_area.config(state="disabled")
            self.text_area.see(tk.END)


    def show_server_message(self, massage):
        if massage.strip():
            self.text_area.config(state="normal")
            self.text_area.insert(tk.END, f"Server message: {massage}\n")
            self.text_area.config(state="disabled")
            self.text_area.see(tk.END)


    def disable_button(self):
        self.send_button.configure(state="disabled")


    def enable_button(self):
        self.send_button.configure(state="normal")


    def start(self):
        self.create_main_interface()
