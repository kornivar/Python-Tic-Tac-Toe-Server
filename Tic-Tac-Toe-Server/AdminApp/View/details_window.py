import tkinter as tk
from ast import Str
from tkinter import ttk
from tkinter import messagebox


class DetailsWindow:
    def __init__(self, controller, root):
        self.controller = controller
        self.root = root

        self.root = tk.Toplevel(root)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.title("Session Details")

        self.window_width = 450
        self.window_height = 500
        self.root.configure(background="#EAF4F9")

        self.players_frame = None
        self.status_label = None
        self.winner_label = None
        self.session_id = None

        self.root.withdraw()


    def create_interface(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.center(self.root, self.window_width, self.window_height)


        header = tk.Frame(self.root, bg="#243B4A", pady=10)
        header.pack(fill="x")

        tk.Label(
            header, text=f"SESSION DETAILS",
            font=("Arial", 12, "bold"), fg="white", bg="#243B4A"
        ).pack()


        info_frame = tk.LabelFrame(self.root, text=" Game Info ", bg="#EAF4F9", padx=10, pady=10)
        info_frame.pack(fill="x", padx=20, pady=10)

        self.status_label = tk.Label(info_frame, text="Status: Unknown", bg="#EAF4F9", font=("Arial", 10))
        self.status_label.pack(anchor="w")

        self.winner_label = tk.Label(info_frame, text="", bg="#EAF4F9", font=("Arial", 10, "bold"), fg="#28a745")
        self.winner_label.pack(anchor="w")


        players_container = tk.LabelFrame(self.root, text=" Players ", bg="#EAF4F9", padx=10, pady=10)
        players_container.pack(fill="both", expand=True, padx=20, pady=5)

        self.players_frame = tk.Frame(players_container, bg="#EAF4F9")
        self.players_frame.pack(fill="both", expand=True)


    def update_info(self, s_data: dict):
        self.session_id = s_data.get("session_id")
        self.root.title(f"Details: Session {self.session_id}")

        state = s_data.get("state", "unknown")
        winner = s_data.get("winner")

        self.status_label.config(text=f"Game State: {state.upper()}")

        if winner:
            text = f"WINNER: Player {winner}" if winner != "draw" else "RESULT: Draw"
            self.winner_label.config(text=text)
        else:
            self.winner_label.config(text="")

        for widget in self.players_frame.winfo_children():
            widget.destroy()

        players = s_data.get("players", {})
        if not players:
            tk.Label(self.players_frame, text="No players in session", bg="#EAF4F9").pack()

        for p_id, p_data in players.items():
            self.create_player_row(p_id, p_data)


    def create_player_row(self, p_id, p_data):
        p_row = tk.Frame(self.players_frame, bg="white", pady=5, padx=5, highlightbackground="#BFDCEB",
                         highlightthickness=1)
        p_row.pack(fill="x", pady=2)

        name = p_data.get("username", "Unknown")
        is_banned = p_data.get("is_banned", False)

        info_text = f"ID: {p_id} | Name: {name}"
        lbl = tk.Label(p_row, text=info_text, bg="white", font=("Arial", 10))
        lbl.pack(side="left", padx=5)

        btn_text = "Ban User"
        btn_bg = "#FF5F5F"

        ban_btn = tk.Button(
            p_row, text=btn_text, bg=btn_bg, fg="white",
            font=("Arial", 8, "bold"), width=10,
            command=lambda s = self.session_id, u=p_id, n = name, b=is_banned: self.controller.toggle_ban(s, u, n, not b)
        )
        ban_btn.pack(side="right", padx=5)


    def hide_window(self):
        self.root.withdraw()


    def start(self, session_data):
        self.create_interface()
        self.update_info(session_data)
        self.root.deiconify()
        self.root.lift()


    @staticmethod
    def center(window, width, height):
        window.update_idletasks()
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")