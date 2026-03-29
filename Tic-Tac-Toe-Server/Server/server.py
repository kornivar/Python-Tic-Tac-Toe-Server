import socket
import json
import threading
import time
import os
import hashlib
import uuid
import base64
from cryptography.fernet import Fernet

from Server.Classes.ClientData import ClientData
from Server.Classes.SessionData import SessionData


def load_config(file_path: str) -> dict:
    with open(file_path, "r") as f:
        return json.load(f)


running = True
AVATAR_DIR = "Avatars"
config = load_config("config.json")
DB_FILE = config["DB_FILE"]
HOST = config["HOST"]
PORT = config["PORT"]

key = config["KEY"].encode('utf-8')
cipher = Fernet(key)

sessions = {}
session_counter = 0


def hash_password(password: str) -> tuple[str, str]:
    salt = os.urandom(16)
    hash_bytes = hashlib.sha256(salt + password.encode()).digest()
    return salt.hex(), hash_bytes.hex()


def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        db = {
            "users": {}
        }

        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=4)

        return db

    with open(DB_FILE, "r") as f:
        return json.load(f)


def save_db(db: dict) -> None:
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)


def receive_avatar(conn, username: str, filename: str, size: int) -> None:
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


def verification(conn, status: bool) -> None:
    global running
    global cipher
    if running:
        packet = {
            "type": "response",
            "data": status
        }
        packet_bytes = json.dumps(packet).encode('utf-8')
        encrypted_packet = cipher.encrypt(packet_bytes)
        conn.sendall(encrypted_packet + b"\n")


def login(conn, username: str, password: str) -> bool:
    db = load_db()

    if username not in db["users"]:
        verification(conn, False)
        return False

    password_bytes = password.encode("utf-8")
    salt = bytes.fromhex(db["users"][username]["salt"])
    salted_password: bytes = salt + password_bytes

    hashed = hashlib.sha256(salted_password).hexdigest()

    if db["users"][username]["password"] == hashed:
        verification(conn, True)
        return True

    verification(conn, False)
    return False


def signup(conn, username: str, password: str) -> bool:
    db = load_db()

    if username in db["users"]:
        verification(conn, False)
        return False

    salt, hashed = hash_password(password)

    db["users"][username] = {
        "password": hashed,
        "salt": salt,
        "avatar": None
    }

    save_db(db)

    verification(conn, True)
    return True


def send_avatar_to_client(conn, username: str) -> None:
    global cipher
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
        packet = {
            "type": "avatar",
            "data": {"exists": False}
        }

        packet_bytes = json.dumps(packet).encode('utf-8')
        encrypted_packet = cipher.encrypt(packet_bytes)
        conn.sendall(encrypted_packet + b"\n")
        return

    with open(avatar_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    packet = {
        "type": "avatar",
        "data": {
            "exists": True,
            "filename": os.path.basename(avatar_path),
            "content": content
        }
    }
    packet_bytes = json.dumps(packet).encode('utf-8')
    encrypted_packet = cipher.encrypt(packet_bytes)
    conn.sendall(encrypted_packet + b"\n")


def set_avatar(username: str, path: str) -> None:
    db = load_db()

    db["users"][username]["avatar"] = path
    save_db(db)


def handle_admin(conn):
    global cipher

    print("Admin connected")

    try:
        while True:
            packet = {
                "type": "sessions",
                "data": list(sessions.keys())
            }
            conn.sendall(cipher.encrypt(json.dumps(packet).encode()) + b"\n")

            time.sleep(2)

    except Exception as e:
        print(f"Admin error: {e}")

    conn.close()


def handle_client(client_data: ClientData, session) -> None:
    global cipher
    conn = client_data.conn
    my_id = client_data.id
    buffer = b""

    print(f"[Session {session.session_id}] Handler started for Player {my_id}")

    while True:

        try:
            data = conn.recv(1024)
            if not data:
                break

            buffer += data

            while b"\n" in buffer:

                message, buffer = buffer.split(b"\n", 1)

                print(f"SERVER: Received encrypted message: {message}")

                decrypted = cipher.decrypt(message)
                decoded = decrypted.decode("utf-8")

                packet = json.loads(decoded)

                p_type = packet.get("type")
                p_data = packet.get("data")

                if p_type == "login":

                    login_success = login(conn, p_data["username"], p_data["password"])

                    if login_success:
                        client_data.is_authenticated = True
                        client_data.username = p_data["username"]

                elif p_type == "signup":

                    login_success = signup(conn, p_data["username"], p_data["password"])

                    if login_success:
                        client_data.is_authenticated = True
                        client_data.username = p_data["username"]

                elif p_type == "ready":

                    if client_data.is_authenticated:

                        client_data.is_ready = True

                        need_avatar = bool(p_data.get("need_avatar", False))
                        print(f"[Session {session.session_id}] Player {my_id} is ready")

                        init_packet = {
                            "type": "init",
                            "data": {
                                "your_id": my_id,
                                "field": session.playing_field
                            }
                        }
                        packet_bytes = json.dumps(init_packet).encode('utf-8')
                        encrypted_packet = cipher.encrypt(packet_bytes)
                        conn.sendall(encrypted_packet + b"\n")

                        if need_avatar:
                            send_avatar_to_client(conn, client_data.username)

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

                    if not client_data.is_ready:
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

                        packet_bytes = json.dumps(update_packet).encode('utf-8')
                        encrypted_packet = cipher.encrypt(packet_bytes)

                        session.broadcast(encrypted_packet)
                    else:
                        error_packet = {
                            "type": "error",
                            "message": "Invalid move"
                        }
                        packet_bytes = json.dumps(error_packet).encode('utf-8')
                        encrypted_packet = cipher.encrypt(packet_bytes)
                        conn.sendall(encrypted_packet + b"\n")

                elif p_type == "avatar":
                    receive_avatar(conn, p_data["username"], p_data["filename"], p_data["size"])

        except Exception as e:
            print(f"[Session {session.session_id}] Error for Player {my_id}: {e}")
            break

    conn.close()


def identify(conn) -> str | None:
    global cipher

    try:
        request = {
            "type": "identify_request"
        }
        conn.sendall(cipher.encrypt(json.dumps(request).encode()) + b"\n")

        buffer = b""
        while b"\n" not in buffer:
            data = conn.recv(1024)
            if not data:
                return None
            buffer += data

        message, _ = buffer.split(b"\n", 1)
        decrypted = cipher.decrypt(message)
        packet = json.loads(decrypted.decode("utf-8"))

        print(f"Received identify response: {packet}")

        if packet.get("type") == "identify":
            role = packet.get("data")
            return role

    except Exception as e:
        print(f"Identify error: {e}")

    return None


def accept_clients() -> None:
    global session_counter, running

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print(f'Server logic online at {HOST}:{PORT}')

    current_waiting_session = None

    while running:
        try:
            conn, addr = server.accept()
            print(f"Connection from {addr}")

            role = identify(conn)

            if role == "admin":
                threading.Thread(target=handle_admin, args=(conn,), daemon=True).start()
                continue

            elif role != "client":
                print("Unknown role, closing connection")
                conn.close()
                continue

            # === ONLY CLIENTS GET SESSIONS ===

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

            thread = threading.Thread(
                target=handle_client,
                args=(client, current_waiting_session),
                daemon=True
            )
            thread.start()

            if player_id == 2:
                current_waiting_session = None

        except Exception as e:
            print(f"Accept error: {e}")


def start() -> None:
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


