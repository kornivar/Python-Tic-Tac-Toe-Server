import socket
import json
import threading
import time

from Server.Classes.ClientData import ClientData
from Server.Classes.SessionData import SessionData

HOST = '127.0.0.1'
PORT = 4000
running = True
DB_FILE = "database.json"

sessions = {} # {session_id: SessionData}
session_counter = 0

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


def handle_client(client_data, session):
    conn = client_data.conn
    my_id = client_data.id
    buffer = ""

    print(f"[Session {session.session_id}] Handler started for Player {my_id}")

    init_packet = {
        "type": "init",
        "data": {
            "your_id": my_id,
            "field": session.playing_field
        }
    }
    conn.sendall((json.dumps(init_packet) + '\n').encode())

    print(f"[Session {session.session_id}] Sent init to Player {my_id}")

    while True:
        try:
            data = conn.recv(1024)
            if not data:
                print(f"[Session {session.session_id}] Player {my_id} disconnected (no data)")
                break

            buffer += data.decode()
            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)

                print(f"[Session {session.session_id}] Server received from Player {my_id}: {message}")

                packet = json.loads(message)

                if packet.get("type") == "move":
                    move_data = packet.get("data")
                    row = move_data.get("row")
                    col = move_data.get("col")

                    if my_id == session.current_turn and session.playing_field[row][col] == 0:
                        session.playing_field[row][col] = my_id
                        winner = session.check_winner()
                        session.current_turn = 2 if session.current_turn == 1 else 1

                        update_packet = {
                            "type": "update",
                            "data": {
                                "field": session.playing_field,
                                "next_turn": session.current_turn,
                                "winner": winner
                            }
                        }
                        session.broadcast(update_packet)
                        print(f"[Session {session.session_id}] Move accepted: {row}:{col}. Next turn: {session.current_turn}")
                    else:
                        error_pkt = {"type": "error", "message": "Invalid move"}
                        conn.sendall((json.dumps(error_pkt) + '\n').encode())

        except Exception as e:
            print(f"[Session {session.session_id}] CRITICAL ERROR in handle_client for Player {my_id}: {e}")
            break

    conn.close()


def accept_clients():
    global session_counter, running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f'Server logic online at {HOST}:{PORT}')

    current_waiting_session = None

    while running:
        try:
            conn, addr = server.accept()

            if current_waiting_session is None:
                session_counter += 1
                current_waiting_session = SessionData(session_counter)
                sessions[session_counter] = current_waiting_session
                player_id = 1
            else:
                player_id = 2

            client = ClientData(conn, addr, player_id, False)
            current_waiting_session.players[player_id] = client

            print(f"Player {player_id} joined session {current_waiting_session.session_id}")

            thread = threading.Thread(target=handle_client, args=(client, current_waiting_session))
            thread.daemon = True
            thread.start()

            if player_id == 2:
                start_packet = {
                    "type": "game_ready",
                    "data": {"status": "started", "first_turn": 1}
                }
                current_waiting_session.broadcast(start_packet)
                current_waiting_session = None

        except Exception as e:
            print(f"Accept error: {e}")


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