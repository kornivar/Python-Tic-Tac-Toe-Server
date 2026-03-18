import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox


class UploadPFPWindow:

    def __init__(self, controller, root):
        self.controller = controller

        self.root = tk.Toplevel(root)
        self.root.title("Upload Avatar")

        self.window_width = 350
        self.window_height = 180

        self.frame = None
        self.file_label = None
        self.file_path = None

        self.choose_button = None
        self.ok_button = None
        self.skip_button = None

        self.root.withdraw()

    def create_interface(self):
        self.root.deiconify()
        self.root.update_idletasks()
        self.center(self.root, self.window_width, self.window_height)

        self.root.configure(background="#EAF4F9")

        self.frame = tk.Frame(self.root, bg="#EAF4F9")
        self.frame.pack(padx=15, pady=15, fill="both", expand=True)

        tk.Label(
            self.frame,
            text="Choose an avatar image",
            bg="#EAF4F9",
            fg="#243B4A",
            font=("Arial", 11)
        ).pack(anchor="center", pady=(0, 10))

        self.file_label = tk.Label(
            self.frame,
            text="No file selected",
            bg="#EAF4F9",
            fg="#243B4A"
        )
        self.file_label.pack(pady=(0, 10))

        self.choose_button = tk.Button(
            self.frame,
            text="Choose File",
            bg="#A0E9FF",
            fg="#243B4A",
            command=self.choose_file
        )
        self.choose_button.pack(pady=(0, 10))

        button_frame = tk.Frame(self.frame, bg="#EAF4F9")
        button_frame.pack(pady=5)

        self.ok_button = tk.Button(
            button_frame,
            text="OK",
            width=10,
            bg="#A0E9FF",
            fg="#243B4A",
            command=self.confirm_avatar
        )
        self.ok_button.pack(side="left", padx=5)

        self.skip_button = tk.Button(
            button_frame,
            text="Continue without avatar",
            bg="#F5F9FC",
            fg="#243B4A",
            command=self.skip_avatar
        )
        self.skip_button.pack(side="left", padx=5)

    def choose_file(self):
        file_path = filedialog.askopenfilename(
            title="Select avatar image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif"),
                ("All files", "*.*")
            ],
            parent=self.root
        )

        if file_path:
            self.file_path = file_path
            self.file_label.config(text=file_path.split("/")[-1])

    def confirm_avatar(self):
        if not self.file_path:
            messagebox.showwarning(
                "No file selected",
                "Please choose an image or continue without avatar.",
                parent=self.root
            )
            return

        self.controller.avatar_selected(self.file_path)
        self.root.destroy()

    def skip_avatar(self):
        self.controller.avatar_selected(None)
        self.root.destroy()

    @staticmethod
    def center(window, width, height):
        window.update_idletasks()
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")

    def start(self):
        self.create_interface()