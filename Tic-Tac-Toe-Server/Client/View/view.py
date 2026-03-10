import tkinter as tk
from tkinter import messagebox


class View:
    def __init__(self, controller, root):
        self.controller = controller
        self.root = tk.Toplevel(root)
        self.root.title('Tic-Tac-Toe Client')

        self.window_width = 400
        self.window_height = 500

        # Grid of buttons
        self.buttons = [[None for _ in range(3)] for _ in range(3)]
        self.status_label = None

        self.root.withdraw()  # Hide until started


    def create_main_interface(self):
        self.root.deiconify()
        self.center(self.root, self.window_width, self.window_height)
        self.root.configure(background="#EAF4F9")

        # Top Status Label ("Waiting for player", "Your turn"...)
        self.status_label = tk.Label(
            self.root,
            text="WAITING FOR OPPONENT...",
            font=("Arial", 14, "bold"),
            bg="#EAF4F9",
            fg="#243B4A",
            pady=20
        )
        self.status_label.pack()

        # Game Board Frame
        grid_frame = tk.Frame(self.root, bg="#BFDCEB", padx=10, pady=10)
        grid_frame.pack(expand=True)

        for row in range(3):
            for col in range(3):
                btn = tk.Button(
                    grid_frame,
                    text="",
                    font=("Arial", 24, "bold"),
                    width=5,
                    height=2,
                    bg="#F5F9FC",
                    command=lambda r=row, c=col: self.on_click(r, c)
                )
                btn.grid(row=row, column=col, padx=5, pady=5)
                self.buttons[row][col] = btn

        self.lock_board("WAITING FOR PLAYERS...")


    def on_click(self, row, col):
        self.controller.send_move(row, col)


    def update_board(self, field):
        for r in range(3):
            for c in range(3):
                symbol = ""
                color = "#243B4A"
                if field[r][c] == 1:
                    symbol = "X"
                    color = "#FF5F5F"  # Red for X
                elif field[r][c] == 2:
                    symbol = "O"
                    color = "#5F9FFF"  # Blue for O

                self.buttons[r][c].config(text=symbol, fg=color)


    def lock_board(self, status_text="OPPONENT'S TURN"):
        self.status_label.config(text=status_text)
        for row in self.buttons:
            for btn in row:
                btn.config(state="disabled")


    def unlock_board(self, status_text="YOUR TURN"):
        self.status_label.config(text=status_text)
        for r in range(3):
            for c in range(3):
                # Only unlock if the cell is empty (empty string)
                if self.buttons[r][c].cget("text") == "":
                    self.buttons[r][c].config(state="normal")
                else:
                    self.buttons[r][c].config(state="disabled")


    def show_winner(self, result):
        if result == "draw":
            messagebox.showinfo("Game Over", "It's a Draw!")
        else:
            messagebox.showinfo("Game Over", f"Player {result} Wins!")
        self.lock_board("GAME OVER")


    @staticmethod
    def center(window, width, height):
        window.update_idletasks()
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")


    def start(self):
        self.create_main_interface()