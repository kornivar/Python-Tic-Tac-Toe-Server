from Model.model import Model
from Controller.controller import Controller
import queue
import json


def load_config(file_path: str):
    with open(file_path, "r") as f:
        return json.load(f)

config = load_config("config.json")
IP = config["IP"]
PORT = config["PORT"]

queue = queue.Queue()

model = Model(IP, PORT, queue)
controller = Controller(model, queue)
controller.start()

