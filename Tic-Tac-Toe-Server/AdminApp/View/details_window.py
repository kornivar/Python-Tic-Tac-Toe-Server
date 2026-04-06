import tkinter as tk

class DetailsWindow:
    def __init__(self, controller, parent_root):
        self.controller = controller
        self.root = parent_root

        self.root = tk.Toplevel(parent_root)
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
        p_row = tk.Frame(self.players_frame, bg="white", pady=5, padx=5,
                         highlightbackground="#BFDCEB", highlightthickness=1)
        p_row.pack(fill="x", pady=2)

        name = p_data.get("username", "Unknown")
        is_banned = p_data.get("is_banned", False)

        stats = {
            "win_rate": p_data.get("win_rate", 0),
            "games": p_data.get("games_played", 0),
            "wins": p_data.get("wins_count", 0),
            "joined": p_data.get("join_date", "Unknown")
        }

        tk.Label(p_row, text=f"ID: {p_id} | Name: {name}", bg="white", font=("Arial", 10)).pack(side="left", padx=5)

        ban_btn = tk.Button(
            p_row, text="Ban User", bg="#FF5F5F", fg="white",
            font=("Arial", 8, "bold"), width=10,
            command=lambda s=self.session_id, u=p_id, n=name, b=is_banned: self.controller.toggle_ban(s, u, n, not b)
        )
        ban_btn.pack(side="right", padx=5)

        more_btn = tk.Button(
            p_row, text="More", bg="#D0E4F0", fg="#243B4A",
            font=("Arial", 8, "bold"), width=8,
            command=lambda n=name, st=stats: self.show_user_stats(n, st)
        )
        more_btn.pack(side="right", padx=5)


    def show_user_stats(self, username, stats):
        stats_win = tk.Toplevel(self.root)
        stats_win.title(f"Stats: {username}")
        stats_win.geometry("250x200")
        stats_win.configure(bg="#F5F9FC")

        tk.Label(stats_win, text=f"User: {username}", font=("Arial", 12, "bold"), bg="#243B4A", fg="white",
                 pady=5).pack(fill="x")

        content = tk.Frame(stats_win, bg="#F5F9FC", padx=20, pady=10)
        content.pack(fill="both", expand=True)

        tk.Label(content, text=f"Games Played: {stats['games']}", bg="#F5F9FC").pack(anchor="w")
        tk.Label(content, text=f"Wins: {stats['wins']}", bg="#F5F9FC").pack(anchor="w")
        tk.Label(content, text=f"Win Rate: {stats['win_rate']}%", bg="#F5F9FC", font=("Arial", 10, "bold")).pack(
            anchor="w")

        date_str = stats['joined'].split('.')[0] if stats['joined'] else "N/A"
        tk.Label(content, text=f"Registered:\n{date_str}", bg="#F5F9FC", fg="#555", justify="left").pack(anchor="w", pady=5)


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