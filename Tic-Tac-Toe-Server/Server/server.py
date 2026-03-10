import socket
import json
import threading
from Server.ClientData import ClientData

HOST = '127.0.0.1'
PORT = 4000
running = True
DB_FILE = "database.json"

playing_field = [
                    [0, 0, 0],
                    [0, 0, 0],
                    [0, 0, 0]
                ]

current_turn = 1
# 2 CLIENTS MAX
client_counter = 0
clients = {}


# def load_db():
#     if not os.path.exists(DB_FILE):
#         db = {
#             "users": {}
#         }
#
#         with open(DB_FILE, "w") as f:
#             json.dump(db, f, indent=4)
#
#         return db
#
#     with open(DB_FILE, "r") as f:
#         return json.load(f)
#
#
# def save_db(db):
#     with open(DB_FILE, "w") as f:
#         json.dump(db, f, indent=4)


def check_winner():
    # rows and columns
    for i in range(3):
        if playing_field[i][0] == playing_field[i][1] == playing_field[i][2] != 0:
            return playing_field[i][0]
        if playing_field[0][i] == playing_field[1][i] == playing_field[2][i] != 0:
            return playing_field[0][i]

    # diagonals
    if playing_field[0][0] == playing_field[1][1] == playing_field[2][2] != 0:
        return playing_field[0][0]
    if playing_field[0][2] == playing_field[1][1] == playing_field[2][0] != 0:
        return playing_field[0][2]

    # draw (no zeros left)
    if not any(0 in row for row in playing_field):
        return "draw"

    return None


# Send a packet to all connected players
def broadcast(payload):
    message = json.dumps(payload) + '\n'
    for client_id in clients:
        try:
            clients[client_id].conn.sendall(message.encode())
        except Exception as e:
            print(f"Broadcast error to client {client_id}: {e}")


def handle_client(client_data):
    global current_turn, playing_field
    conn = client_data.conn
    my_id = client_data.id
    buffer = ""

    # Send initial connection packet
    init_packet = {
        "type": "init",
        "data": {
            "your_id": my_id,
            "field": playing_field
        }
    }
    conn.sendall((json.dumps(init_packet) + '\n').encode())

    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break

            buffer += data.decode()
            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)
                packet = json.loads(message)

                if packet["type"] == "move":
                    move_data = packet["data"]
                    row, col = move_data["row"], move_data["col"]

                    # Validate turn and empty cell
                    if my_id == current_turn and playing_field[row][col] == 0:
                        playing_field[row][col] = my_id

                        winner = check_winner()
                        # Switch turns (1 to 2 or 2 to 1)
                        current_turn = 2 if current_turn == 1 else 1

                        # Broadcast update packet
                        update_packet = {
                            "type": "update",
                            "data": {
                                "field": playing_field,
                                "next_turn": current_turn,
                                "winner": winner
                            }
                        }
                        broadcast(update_packet)
                    else:
                        # Send error if move is invalid
                        error_packet = {
                            "type": "error",
                            "message": "Invalid move or not your turn"
                        }
                        conn.sendall((json.dumps(error_packet) + '\n').encode())

        except Exception as e:
            print(f"Error handling client {my_id}: {e}")
            break

    conn.close()


def accept_clients():
    global client_counter, running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f'Server logic online at {HOST}:{PORT}')

    # Limit to 2 players
    while running and client_counter < 2:
        try:
            conn, addr = server.accept()
            client_counter += 1

            # Create ClientData instance
            client = ClientData(conn, addr, client_counter, False)
            clients[client_counter] = client

            print(f"Player {client_counter} joined from {addr}")

            thread = threading.Thread(target=handle_client, args=(client,))
            thread.daemon = True
            thread.start()
        except Exception as e:
            print(f"Accept error: {e}")

    print("Player limit reached. Accepting thread closed.")


if __name__ == "__main__":
    # Using a thread for accepting to keep main thread free
    accept_thread = threading.Thread(target=accept_clients)
    accept_thread.start()