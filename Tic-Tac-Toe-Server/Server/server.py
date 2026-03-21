import socket
import json
import threading
import time
import os
import hashlib
import uuid
import base64

from Server.Classes.ClientData import ClientData
from Server.Classes.SessionData import SessionData

HOST = '127.0.0.1'
PORT = 4000
running = True
DB_FILE = "database.json"
AVATAR_DIR = "avatars"

sessions = {} # session_id: SessionData
session_counter = 0


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_db():
    if not os.path.exists(DB_FILE):
        db = {
            "users": {}
        }

        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=4)

        return db

    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)


def receive_avatar(conn, username, filename, size):
    ext = filename.split(".")[-1]
    unique_name = str(uuid.uuid4()) + "." + ext

    path = os.path.join(AVATAR_DIR, unique_name)

    received = 0

    with open(path, "wb") as f:
        while received < size:

            chunk = conn.recv(min(4096, size - received))

            if not chunk:
                break

            f.write(chunk)
            received += len(chunk)

    set_avatar(username, path)


def verification(conn, status):
    global running
    if running:
        temp_packet = {
            "type": "response",
            "data": status
        }
        packet = json.dumps(temp_packet)
        conn.sendall((packet + '\n').encode())


def login(conn, username, password):
    db = load_db()

    if username not in db["users"]:
        verification(conn, False)
        return False

    hashed = hash_password(password)

    if db["users"][username]["password"] == hashed:
        verification(conn, True)
        return True

    verification(conn, False)
    return False


def signup(conn, username, password):
    db = load_db()

    if username in db["users"]:
        verification(conn, False)
        return False

    hashed = hash_password(password)

    db["users"][username] = {
        "password": hashed,
        "avatar": None
    }

    save_db(db)

    verification(conn, True)
    return True


# def to_packet(data, d_type="message"):
#     if d_type == "request":
#         packet = {
#             "type": "request",
#             "data": data
#         }
#         return json.dumps(packet)
#     elif d_type == "message":
#         packet = {
#             "type": "message",
#             "data": data
#         }
#         return json.dumps(packet)
#
#     return None


def send_avatar_to_client(conn, username):
    db = load_db()
    user = db["users"].get(username)

    if not user:
        pkt = {
            "type": "avatar",
            "data": {"exists": False}
        }
        conn.sendall((json.dumps(pkt) + '\n').encode())
        return

    avatar_path = user.get("avatar")
    if not avatar_path or not os.path.exists(avatar_path):
        pkt = {
            "type": "avatar",
            "data": {"exists": False}
        }
        conn.sendall((json.dumps(pkt) + '\n').encode())
        return

    with open(avatar_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    pkt = {
        "type": "avatar",
        "data": {
            "exists": True,
            "filename": os.path.basename(avatar_path),
            "content": content
        }
    }
    conn.sendall((json.dumps(pkt) + '\n').encode())


def set_avatar(username, path):
    db = load_db()

    db["users"][username]["avatar"] = path
    save_db(db)


def handle_client(client_data, session):
    conn = client_data.conn
    my_id = client_data.id
    buffer = ""
    is_authenticated = False
    is_ready = False
    current_username = None

    print(f"[Session {session.session_id}] Handler started for Player {my_id}")

    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break

            buffer += data.decode()
            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)
                packet = json.loads(message)
                p_type = packet.get("type")
                p_data = packet.get("data")

                if p_type == "login":
                    login_success = login(conn, p_data["username"], p_data["password"])
                    if login_success:
                        is_authenticated = True
                        current_username = p_data["username"]

                elif p_type == "signup":
                    login_success = signup(conn, p_data["username"], p_data["password"])
                    if login_success:
                        is_authenticated = True
                        current_username = p_data["username"]

                elif p_type == "ready":
                    if is_authenticated:
                        is_ready = True
                        need_avatar = bool(p_data.get("need_avatar", False))
                        print(f"[Session {session.session_id}] Player {my_id} is ready")

                        init_packet = {
                            "type": "init",
                            "data": {
                                "your_id": my_id,
                                "field": session.playing_field
                            }
                        }
                        conn.sendall((json.dumps(init_packet) + '\n').encode())

                        if need_avatar:
                            send_avatar_to_client(conn, current_username)

                        session.ready_players.add(my_id)

                        if len(session.ready_players) == 2:
                            start_packet = {
                                "type": "game_ready",
                                "data": {"status": "started", "first_turn": 1}
                            }
                            session.broadcast(start_packet)
                            print(f"[Session {session.session_id}] All players ready. Game started.")
                    else:
                        error_pkt = {"type": "error", "message": "Login required before ready"}
                        conn.sendall((json.dumps(error_pkt) + '\n').encode())

                elif p_type == "move":
                    if not is_ready:
                        continue

                    row, col = p_data.get("row"), p_data.get("col")
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
                    else:
                        error_pkt = {"type": "error", "message": "Invalid move"}
                        conn.sendall((json.dumps(error_pkt) + '\n').encode())

                elif p_type == "avatar":
                    receive_avatar(conn, p_data["username"], p_data["filename"], p_data["size"])

        except Exception as e:
            print(f"[Session {session.session_id}] Error for Player {my_id}: {e}")
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