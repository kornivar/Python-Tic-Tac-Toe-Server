from Client.View.view import View
import tkinter as tk

class Controller:
    def __init__(self, model, queue):
        self.model = model
        self.queue = queue

        self.root = tk.Tk()
        self.root.withdraw()

        self.view = View(self, self.root)
        self.my_id = None
        self.is_game_started = False


    def poll_queue(self):
        # Processes incoming packets from the Model
        while not self.queue.empty():
            packet = self.queue.get()
            print(f"DEBUG: Received packet: {packet}")
            p_type = packet.get("type")
            p_data = packet.get("data")

            if p_type == "init":
                # Store our player ID (1 or 2)
                self.my_id = p_data["your_id"]
                self.view.status_label.config(text=f"CONNECTED AS PLAYER {self.my_id}")

            elif p_type == "game_ready":
                self.is_game_started = True
                if self.my_id == 1:
                    self.view.unlock_board("YOUR TURN")
                else:
                    self.view.lock_board("WAITING FOR PLAYER 1...")

            elif p_type == "update":
                # Update board and check turns
                field = p_data["field"]
                next_turn = p_data["next_turn"]
                winner = p_data["winner"]

                self.view.update_board(field)

                if winner:
                    self.view.show_winner(winner)
                    self.is_game_started = False
                elif next_turn == self.my_id:
                    self.view.unlock_board("YOUR TURN")
                else:
                    self.view.lock_board("OPPONENT'S TURN")

            elif p_type == "error":
                # Show server-side errors
                print(f"Server Error: {packet.get('message')}")

        # Continue polling
        self.root.after(100, self.poll_queue)

    def send_move(self, row, col):
        # Sends move coordinates to the game server
        if self.is_game_started:
            self.model.send_move(row, col)
            # Lock immediately after clicking to prevent double clicks
            self.view.lock_board("SENDING MOVE...")

    def check_connection(self):
        # Checks if model successfully connected to server
        if self.model.is_connected():
            print("Connected to server successfully.")
            self.poll_queue()
        else:
            # Keep checking until connection is established
            self.root.after(500, self.check_connection)

    def start(self):
        self.view.start()
        self.model.start()
        self.check_connection()
        self.root.mainloop()

    def stop(self):
        self.model.stop()
        self.root.destroy()