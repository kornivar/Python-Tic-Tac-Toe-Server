from Model.model import Model
from Controller.controller import Controller
import queue
import json
from cryptography.fernet import Fernet

def load_config(file_path: str) -> dict:
    with open(file_path, "r") as f:
        return json.load(f)

config = load_config("config.json")
IP = config["IP"]
PORT = config["PORT"]
key = config["KEY"].encode('utf-8')
cipher = Fernet(key)

queue = queue.Queue()

model = Model(IP, PORT, queue, cipher)
controller = Controller(model, queue)
controller.start()


