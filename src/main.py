from client import Client
from server import Server

if __name__ == "__main__":
    client = Client()
    server = Server()

    # Start background processes
    client.start()
    server.start()

    # Interact with client
    client.interact()

    # Terminate client and server processes when client interaction is done
    client.stop()
    server.stop()
