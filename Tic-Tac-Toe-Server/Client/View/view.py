import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw, ImageOps


class View:
    def __init__(self, controller, root):
        self.controller = controller
        self.root = tk.Toplevel(root)
        self.root.protocol("WM_DELETE_WINDOW", self.controller.on_closing)
        self.root.title('Tic-Tac-Toe Client')

        self.window_width = 400
        self.window_height = 500

        self.avatar_canvas = None
        self.avatar_circle = None
        self.tk_image = None
        self.buttons = [[None for _ in range(3)] for _ in range(3)]
        self.status_label = None

        self.root.withdraw()


    def create_main_interface(self) -> None:
        self.root.deiconify()
        self.center(self.root, self.window_width, self.window_height)
        self.root.configure(background="#EAF4F9")

        top_bar = tk.Frame(self.root, bg="#EAF4F9", padx=20, pady=15)
        top_bar.pack(fill="x")

        self.avatar_canvas = tk.Canvas(
            top_bar,
            width=70,
            height=70,
            bg="#EAF4F9",
            highlightthickness=0
        )
        self.avatar_canvas.pack(side="left")

        self.avatar_circle = self.avatar_canvas.create_oval(
            2, 2, 68, 68, fill="", outline="#243B4A", width=2
        )

        self.status_label = tk.Label(
            top_bar,
            text="WAITING FOR OPPONENT...",
            font=("Arial", 12, "bold"),
            bg="#EAF4F9",
            fg="#243B4A",
            padx=15
        )
        self.status_label.pack(side="left")

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
                    activebackground="#D0E4F0",
                    command=lambda r=row, c=col: self.on_click(r, c)
                )
                btn.grid(row=row, column=col, padx=5, pady=5)
                self.buttons[row][col] = btn

        self.lock_board("WAITING FOR PLAYERS...")


    def update_avatar(self, image_path: str) -> None:
        try:
            size = (66, 66)

            img = Image.open(image_path).convert("RGBA")
            resample_filter = getattr(Image, "Resampling", Image).LANCZOS
            img = ImageOps.fit(img, size, method=resample_filter)

            mask = Image.new("L", size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size[0], size[1]), fill=255)
            img.putalpha(mask)

            self.tk_image = ImageTk.PhotoImage(img)

            self.avatar_canvas.delete("avatar_img")
            self.avatar_canvas.create_image(
                35, 35,
                image=self.tk_image,
                tags="avatar_img"
            )
            self.avatar_canvas.tag_lower("avatar_img", self.avatar_circle)

        except Exception as e:
            print(f"Error in update_avatar function: {e}")


    def on_click(self, row: int, col: int) -> None:
        self.controller.send_move(row, col)


    def update_board(self, field: list) -> None:
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


    def lock_board(self, status_text="OPPONENT'S TURN") -> None:
        self.status_label.config(text=status_text)
        for row in self.buttons:
            for btn in row:
                btn.config(state="disabled")


    def unlock_board(self, status_text="YOUR TURN") -> None:
        self.status_label.config(text=status_text)
        for r in range(3):
            for c in range(3):
                # Only unlock if the cell is empty (empty string)
                if self.buttons[r][c].cget("text") == "":
                    self.buttons[r][c].config(state="normal")
                else:
                    self.buttons[r][c].config(state="disabled")


    def show_winner(self, result: str) -> None:
        if result == "draw":
            messagebox.showinfo("Game Over", "It's a Draw!")
        else:
            messagebox.showinfo("Game Over", f"Player {result} Wins!")
        self.lock_board("GAME OVER")


    def show_error(self, message: str) -> None:
        messagebox.showerror("Error", message)


    @staticmethod
    def center(window, width: int, height: int) -> None:
        window.update_idletasks()
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")


    def update_player_name(self, name: str) -> None:
        self.root.title(name)


    def start(self):
        self.create_main_interface()