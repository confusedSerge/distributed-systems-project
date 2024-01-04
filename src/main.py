from multiprocessing import Process

from util.helper import load_config

from client import Client
from server import Server


if __name__ == "__main__":
    # Load configuration
    config = load_config()

    server = Server(config=config)
    client = Client(config=config)

    # Start background processes
    server.start()
    client.start()

    # Interact with client
    client.interact()

    # Terminate client and server processes when client interaction is done
    server.terminate()
    client.terminate()
