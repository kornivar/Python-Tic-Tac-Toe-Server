from Client.Model.model import Model
from Client.Controller.controller import Controller
import json
from cryptography.fernet import Fernet


def load_config(file_path: str) -> dict:
    with open(file_path, "r") as f:
        return json.load(f)

def main():
    import queue

    config = load_config("config.json")
    IP = config["IP"]
    PORT = config["PORT"]
    key = config["KEY"].encode('utf-8')
    cipher = Fernet(key)

    queue = queue.Queue()

    model = Model(IP, PORT, queue, cipher)
    controller = Controller(model, queue)
    controller.start()

if __name__ == "__main__":
    main()

