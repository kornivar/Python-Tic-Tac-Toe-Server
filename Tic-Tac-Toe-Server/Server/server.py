import socket
import json
import threading
import time
import os
import hashlib
import uuid
import base64
import pyodbc
from cryptography.fernet import Fernet

from Server.Classes.Client import Client
from Server.Classes.SessionData import SessionData
from Server.Classes.Admin import Admin

def load_config(file_path: str) -> dict:
    with open(file_path, "r") as f:
        return json.load(f)


running = True
AVATAR_DIR = "Avatars"
config = load_config("config.json")
HOST = config["HOST"]
PORT = config["PORT"]

key = config["KEY"].encode('utf-8')
cipher = Fernet(key)

SQL_SERVER = config["SQL_SERVER"]
SQL_DATABASE = config["SQL_DATABASE"]
CONN_STR = (
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={SQL_SERVER};'
    f'DATABASE={SQL_DATABASE};'
    'Trusted_Connection=yes;'
)


def get_db_connection():
    return pyodbc.connect(CONN_STR)

def load_banned_users():
    db_conn = None
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        cursor.execute("SELECT username FROM Users WHERE is_banned = 1")
        return [row.username for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error loading banned users: {e}")
        return []
    finally:
        if db_conn: db_conn.close()


sessions: dict = {}
banned_users: list = load_banned_users()
session_counter: int = 0


def hash_password(password: str) -> tuple[str, str]:
    salt = os.urandom(16)
    hash_bytes = hashlib.sha256(salt + password.encode()).digest()
    return salt.hex(), hash_bytes.hex()


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


def send_banned_warning(conn) -> None:
    global running
    global cipher

    if running:
        packet = {
            "type": "response",
            "data": "banned"
        }

        packet_bytes = json.dumps(packet).encode('utf-8')
        encrypted_packet = cipher.encrypt(packet_bytes)
        conn.sendall(encrypted_packet + b"\n")

def login(conn_socket, username: str, password: str, role: str) -> bool:
    if username in banned_users:
        print(f"Login denied for banned user: {username}")
        send_banned_warning(conn_socket)
        # verification(conn_socket, False)
        time.sleep(0.1)
        conn_socket.close()
        return False

    db_conn = None

    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        row = None

        if role == "user":
            cursor.execute("SELECT password_hash, salt FROM Users WHERE username = ?", (username,))
            row = cursor.fetchone()
        elif role == "admin":
            cursor.execute("SELECT password_hash, salt FROM Admins WHERE username = ?", (username,))
            row = cursor.fetchone()

        if not row:
            verification(conn_socket, False)
            return False

        db_password_hash = row.password_hash
        db_salt = row.salt

        # Check the password
        salted_password = bytes.fromhex(db_salt) + password.encode("utf-8")
        current_hash = hashlib.sha256(salted_password).hexdigest()

        if db_password_hash == current_hash:
            verification(conn_socket, True)
            return True

        verification(conn_socket, False)
        return False

    except Exception as e:
        print(f"Database error during login: {e}")
        return False

    finally:
        if db_conn:
            db_conn.close()


def signup(conn_socket, username: str, password: str) -> bool:
    salt, hashed = hash_password(password)
    db_conn = None

    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()

        # Check if this user already exists
        cursor.execute("SELECT username FROM Users WHERE username = ?", (username,))
        if cursor.fetchone():
            verification(conn_socket, False)
            return False

        # Add user
        cursor.execute(
            "INSERT INTO Users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, hashed, salt)
        )

        # Commit changes to DB and send verification respond
        db_conn.commit()
        verification(conn_socket, True)
        return True

    except Exception as e:
        print(f"Database error during signup: {e}")
        if db_conn:
            db_conn.rollback()  # ROLLBACK changes
        verification(conn_socket, False)
        return False
    finally:
        if db_conn:
            db_conn.close()


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


def send_avatar_to_client(conn_socket, username: str) -> None:
    global cipher
    db_conn = None
    avatar_path = None
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        cursor.execute("SELECT avatar_path FROM Users WHERE username = ?", (username,))
        row = cursor.fetchone()

        if row:
            avatar_path = row

    except Exception as e:
        print(f"Database error in send_avatar_to_client: {e}")

    finally:
        if db_conn:
            db_conn.close()

    try:
        if not avatar_path or not os.path.exists(avatar_path):
            packet = {"type": "avatar", "data": {"exists": False}}
            encrypted_packet = cipher.encrypt(json.dumps(packet).encode('utf-8'))
            conn_socket.sendall(encrypted_packet + b"\n")
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
        encrypted_packet = cipher.encrypt(json.dumps(packet).encode('utf-8'))
        conn_socket.sendall(encrypted_packet + b"\n")

    except Exception as e:
        print(f"Error reading or sending avatar file: {e}")


def set_avatar(username: str, path: str) -> None:
    db_conn = None

    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()

        cursor.execute("UPDATE Users SET avatar_path = ? WHERE username = ?", (path, username))
        db_conn.commit()
        print(f"Avatar path updated for user {username}")

    except Exception as e:
        print(f"Database error in set_avatar: {e}")
        if db_conn:
            db_conn.rollback()

    finally:
        if db_conn:
            db_conn.close()


def update_user_ban_status(username: str, status: bool):
    db_conn = None
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        cursor.execute("UPDATE Users SET is_banned = ? WHERE username = ?", (1 if status else 0, username))
        db_conn.commit()

        global banned_users
        if status and username not in banned_users:
            banned_users.append(username)
        elif not status and username in banned_users:
            banned_users.remove(username)

        print(f"Database: User {username} ban status updated to {status}")
        return True
    except Exception as e:
        print(f"Database error while updating ban: {e}")
        return False
    finally:
        if db_conn: db_conn.close()


def handle_admin(admin: Admin):
    global cipher, sessions, banned_users

    conn = admin.conn
    buffer = b""
    print("Admin connected")

    stop_event = threading.Event()
    session_data_sender = threading.Thread(target=admin.update_sessions, args=[sessions, banned_users, cipher, stop_event], daemon=True)

    try:
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break

                buffer += data

                while b"\n" in buffer:
                    message, buffer = buffer.split(b"\n", 1)

                    print(f"SERVER: Received encrypted message from ADMIN: {message}")

                    decrypted = cipher.decrypt(message)
                    decoded = decrypted.decode("utf-8")

                    packet = json.loads(decoded)

                    p_type = packet.get("type")
                    p_data = packet.get("data")

                    if p_type == "login":
                        login_success = login(conn, p_data["username"], p_data["password"], "admin")

                        if login_success:
                            admin.is_authenticated = True
                            session_data_sender.start()

                    elif p_type == "admin_command":
                        s_id = p_data.get("session_id", None)
                        session = None

                        if s_id:
                            try:
                                s_id = int(s_id)
                            except:
                                pass

                            if s_id not in sessions:
                                print(f"Admin tried to manage non-existent session {s_id}")
                                continue

                            session = sessions[s_id]

                        if p_data["type"] == "session":
                            state_cmd = p_data["state"]
                            if state_cmd == "pause":
                                if session.state not in ["paused", "inactive", "finished"]:
                                    session.pause_session(cipher)
                                else:
                                    print(f"Session {s_id} cannot be paused from state {session.state}")

                            elif state_cmd == "resume":
                                if session.state == "paused":
                                    session.resume_session(cipher)
                                else:
                                    print(f"Session {s_id} is not paused")

                        elif p_data["type"] == "user":
                            u_id_raw = p_data.get("user_id", None)
                            u_name = p_data.get("username")
                            u_id = None

                            if u_id_raw:
                                try:
                                    u_id = int(u_id_raw)
                                except (ValueError, TypeError):
                                    u_id = u_id_raw

                            if p_data["action"] == "ban":
                                if update_user_ban_status(u_name, True):

                                    print(f"User {u_name} banned.")

                                    if u_id in session.players:
                                        session.remove_player_from_session(u_id, sessions, cipher)
                                        print(f"User {u_name} kicked from active session.")
                                    else:
                                        print(f"DEBUG: Player {u_id} ({type(u_id)}) not found in {list(session.players.keys())}")

                            elif p_data["action"] == "unban":
                                update_user_ban_status(u_name, False)
                                print(f"User {u_name} unbanned.")

            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError):
                print(f"DEBUG: Admin connection reset.")
                break

    except Exception as e:
        print(f"Admin error: {e}")

    finally:
        admin.is_authenticated = False

    stop_event.set()
    session_data_sender.join(timeout=3)

    if session_data_sender.is_alive():
        print("Could not close data_sender thread, closing connection without joining")
    else:
        print("Joined data_sender thread, closing connection")

    try:
        conn.close()
    except Exception as e:
        print(f"[Could not close connection in ADMIN] Error: {e}")


def handle_client(client: Client, session) -> None:
    global cipher, sessions

    conn = client.conn
    my_id = client.id
    buffer = b""

    print(f"[Session {session.session_id}] Handler started for Player {my_id}")

    try:
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    print(f"DEBUG: Player {my_id} sent empty data (connection closed).")
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

                        login_success = login(conn, p_data["username"], p_data["password"], "user")

                        if login_success:
                            client.is_authenticated = True
                            client.username = p_data["username"]

                    elif p_type == "signup":

                        login_success = signup(conn, p_data["username"], p_data["password"])

                        if login_success:
                            client.is_authenticated = True
                            client.username = p_data["username"]

                    elif p_type == "ready":

                        if client.is_authenticated:

                            client.is_ready = True

                            need_avatar = bool(p_data.get("need_avatar", False))
                            print(f"[Session {session.session_id}] Player {my_id} is ready")

                            init_packet = {
                                "type": "init",
                                "data": {
                                    "your_id": my_id,
                                    "field": session.playing_field,
                                    "next_turn": 1
                                }
                            }
                            packet_bytes = json.dumps(init_packet).encode('utf-8')
                            encrypted_packet = cipher.encrypt(packet_bytes)
                            conn.sendall(encrypted_packet + b"\n")

                            if need_avatar:
                                send_avatar_to_client(conn, client.username)

                            session.ready_players.add(my_id)

                            if len(session.ready_players) == 2:
                                session.state = "active"
                                start_packet = {
                                    "type": "game_ready",
                                    "data": {"next_turn": 1}
                                }
                                packet_bytes = json.dumps(start_packet).encode('utf-8')
                                encrypted_packet = cipher.encrypt(packet_bytes)
                                session.broadcast(encrypted_packet)
                                print(f"[Session {session.session_id}] All players ready. Game started.")

                        else:
                            error_pkt = {"type": "error", "message": "Login required before ready"}
                            conn.sendall((json.dumps(error_pkt) + '\n').encode())

                    elif p_type == "move":
                        if not client.is_ready:
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
                                "data": {
                                    "message": "Invalid move"
                                }
                            }
                            packet_bytes = json.dumps(error_packet).encode('utf-8')
                            encrypted_packet = cipher.encrypt(packet_bytes)
                            conn.sendall(encrypted_packet + b"\n")

                    elif p_type == "avatar":
                        receive_avatar(conn, p_data["username"], p_data["filename"], p_data["size"])
            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError):
                print(f"DEBUG: Player {my_id} connection reset.")
                break

    except Exception as e:
        print(f"[Session {session.session_id}] Error for Player {my_id}: {e}")

    finally:
        print(f"[Session {session.session_id}] Player {my_id} disconnected.")
        with threading.Lock():
            if my_id in session.players:
                del session.players[my_id]

            if len(session.players) == 0:
                print(f"[Session {session.session_id}] No players left. Closing session.")
                if session.session_id in sessions:
                    del sessions[session.session_id]
            else:
                session.reset_session()
                disconnect_msg = {
                    "type": "game_error",
                    "data": {
                        "message": "player disconnected"
                    }
                }
                packet_bytes = json.dumps(disconnect_msg).encode('utf-8')
                encrypted_packet = cipher.encrypt(packet_bytes)
                session.broadcast(encrypted_packet)

    try:
        conn.close()
    except Exception as e:
        print(f"[Could not close connection in {session.session_id}] Error: {e}")


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
    global session_counter, running, sessions

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print(f'Server logic online at {HOST}:{PORT}')

    while running:
        try:
            conn, addr = server.accept()
            conn.settimeout(5.0)
            print(f"Connection from {addr}")

            role = identify(conn)

            if role == "admin":
                admin = Admin(conn, addr)
                admin.role = role
                threading.Thread(
                    target=handle_admin,
                    args=(admin,),
                    daemon=True
                ).start()
                continue

            elif role != "user":
                print("Unknown role, closing connection")
                conn.close()
                continue

            # === SESSIONS FOR CLIENTS ===

            target_session = None
            player_id = 1

            for s_id, s_obj in sessions.items():
                if len(s_obj.players) < 2:
                    target_session = s_obj
                    player_id = 1 if 1 not in s_obj.players else 2
                    break

            if target_session is None:
                session_counter += 1
                target_session = SessionData(session_counter)
                sessions[session_counter] = target_session
                player_id = 1

            client = Client(conn, addr, player_id, False)
            client.role = role
            target_session.players[player_id] = client

            print(f"Player {player_id} joined session {target_session.session_id}")

            threading.Thread(
                target=handle_client,
                args=(client, target_session),
                daemon=True
            ).start()

        except Exception as e:
            print(f"Accept error: {e}")


def start() -> None:
    global running
    running = True

    accept_thread = threading.Thread(target=accept_clients, daemon=True)
    accept_thread.start()

    try:
        while running:
            time.sleep(2)
    except KeyboardInterrupt:
        print("Server shutting down...")
        running = False

start()


