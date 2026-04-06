import pyodbc

class Client:
    def __init__(self, conn, addr, id, is_win):
        self._conn = conn
        self._addr = addr
        self._id = id
        self.is_win = is_win
        self.is_authenticated = False
        self.is_ready = False
        self.username = None
        self.role = None
        self.is_banned = False
        self.win_rate = 0
        self.wins_count = 0
        self.games_played = 0
        self.join_date = ""

    def to_dict(self):
        return {
            "id": self._id,
            "is_win": self.is_win,
            "username": self.username,
            "is_banned": self.is_banned,
            "win_rate": self.win_rate,
            "wins_count": self.wins_count,
            "games_played": self.games_played,
            "join_date": self.join_date,
        }


    def ban_unban(self, action: str):
        if action == "ban":
            self.is_banned = True
        else:
            self.is_banned = False


    def update_db_stats(self, conn_str, is_winner: bool):
        db_conn = None
        try:
            db_conn = pyodbc.connect(conn_str)
            cursor = db_conn.cursor()

            sql = """
                  UPDATE Users
                  SET games_played = games_played + 1,
                      wins_count   = wins_count + ?,
                      win_rate     = ((wins_count + ?) * 100) / (games_played + 1)
                  WHERE username = ? \
                  """

            win_inc = 1 if is_winner else 0
            cursor.execute(sql, (win_inc, win_inc, self.username))
            db_conn.commit()

            if is_winner:
                self.wins_count += 1
            self.win_rate = int((self.wins_count * 100) / self.games_played)
            print(f"Stats updated in DB for user: {self.username}")

        except Exception as e:
            print(f"Error updating stats for {self.username}: {e}")
            if db_conn:
                db_conn.rollback()
        finally:
            if db_conn:
                db_conn.close()



    @property
    def conn(self):
        return self._conn

    @property
    def addr(self):
        return self._addr

    @property
    def id(self):
        return self._id