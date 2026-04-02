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

    def to_dict(self):
        return {
            "id": self._id,
            "is_win": self.is_win,
            "username": self.username
        }

    @property
    def conn(self):
        return self._conn

    @property
    def addr(self):
        return self._addr

    @property
    def id(self):
        return self._id