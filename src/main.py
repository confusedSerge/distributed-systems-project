from multiprocessing import Process

from client import Client
from server import Server

import time
from util import Timeout


if __name__ == "__main__":
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("", 7778))
    s.settimeout(2)

    try:
        r = s.recv(1024)
        print("Received", r)
    except TimeoutError:
        print("Timeout")
    # client = Client()
    # server = Server()

    # # Start background processes
    # client.start()
    # server.start()

    # # Interact with client
    # client.interact()

    # # Terminate client and server processes when client interaction is done
    # client.stop()
    # server.terminate()
