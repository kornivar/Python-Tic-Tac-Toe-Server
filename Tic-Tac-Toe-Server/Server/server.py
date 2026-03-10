import socket
import json
import threading
import time

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

    print(f"Handler started for Player {my_id}")

    init_packet = {
        "type": "init",
        "data": {
            "your_id": my_id,
            "field": playing_field
        }
    }
    conn.sendall((json.dumps(init_packet) + '\n').encode())
    print(f"Sent init to Player {my_id}")
    # -------------------------------------------------

    while True:
        try:
            data = conn.recv(1024)
            if not data:
                print(f"Player {my_id} disconnected (no data)")
                break

            buffer += data.decode()
            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)
                print(f"Server received from Player {my_id}: {message}")

                packet = json.loads(message)

                if packet.get("type") == "move":
                    move_data = packet.get("data")
                    row = move_data.get("row")
                    col = move_data.get("col")

                    if my_id == current_turn and playing_field[row][col] == 0:
                        playing_field[row][col] = my_id
                        winner = check_winner()
                        current_turn = 2 if current_turn == 1 else 1

                        update_packet = {
                            "type": "update",
                            "data": {
                                "field": playing_field,
                                "next_turn": current_turn,
                                "winner": winner
                            }
                        }
                        broadcast(update_packet)
                        print(f"Move accepted: {row}:{col}. Next turn: {current_turn}")
                    else:
                        error_pkt = {"type": "error", "message": "Invalid move"}
                        conn.sendall((json.dumps(error_pkt) + '\n').encode())

        except Exception as e:
            print(f"CRITICAL ERROR in handle_client for Player {my_id}: {e}")
            import traceback
            traceback.print_exc()
            break

    conn.close()


def accept_clients():
    global client_counter, running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f'Server logic online at {HOST}:{PORT}')

    # Limit 2 players
    while running and client_counter < 2:
        try:
            conn, addr = server.accept()
            client_counter += 1

            client = ClientData(conn, addr, client_counter, False)
            clients[client_counter] = client

            print(f"Player {client_counter} joined from {addr}")

            # Start a thread to handle client
            thread = threading.Thread(target=handle_client, args=(client,))
            thread.daemon = True
            thread.start()

            # CHECK IF BOTH PLAYERS ARE CONNECTED
            if client_counter == 2:
                print("Both players connected. Notifying clients to start game...")

                # Prepare the start packet
                start_packet = {
                    "type": "game_ready",
                    "data": {
                        "status": "started",
                        "first_turn": 1  # Player 1 always starts
                    }
                }
                # Broadcast to both players so they can unlock their UI
                broadcast(start_packet)

        except Exception as e:
            print(f"Accept error: {e}")

    print("Player limit reached. Accepting thread closed.")


def start():
    global running
    running = True

    accept_thread = threading.Thread(target=accept_clients, daemon=True)
    accept_thread.start()

    print("Server is active and keeping threads alive...")
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server shutting down...")
        running = False


start()