import tkinter as tk


class BlacklistWindow:
    def __init__(self, controller, root):
        self.controller = controller
        self.root = tk.Toplevel(root)
        self.root.title("Global Blacklist")
        self.root.geometry("350x450")
        self.root.configure(background="#EAF4F9")
        self.root.withdraw()

        self.root.protocol("WM_DELETE_WINDOW", self.root.withdraw)

        self.list_frame = None
        self.create_main_interface()


    def create_main_interface(self):
        header = tk.Label(self.root, text="Banned Users", font=("Arial", 12, "bold"),
                          bg="#243B4A", fg="white", pady=10)
        header.pack(fill="x")

        self.list_frame = tk.Frame(self.root, bg="#EAF4F9", padx=10, pady=10)
        self.list_frame.pack(fill="both", expand=True)


    def update_list(self, banned_users: list) -> None:
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not banned_users:
            tk.Label(self.list_frame, text="No users in blacklist", bg="#EAF4F9", fg="gray").pack(pady=20)
            return

        for username in banned_users:
            row = tk.Frame(self.list_frame, bg="white", pady=5, padx=5, highlightbackground="#BFDCEB",
                           highlightthickness=1)
            row.pack(fill="x", pady=2)

            tk.Label(row, text=username, bg="white", font=("Arial", 10)).pack(side="left", padx=5)

            tk.Button(
                row, text="Unban", bg="#4CAF50", fg="white", font=("Arial", 8, "bold"),
                command=lambda u=username: self.controller.unban_user(u)
            ).pack(side="right")


    def show(self):
        self.root.deiconify()
        self.root.lift()