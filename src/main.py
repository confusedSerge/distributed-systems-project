from client import Client
from server import Server

if __name__ == "__main__":

    client = Client()
    server = Server()

    # Start background processes
    server.start()
    client.run()

    # Terminate client and server processes when client interaction is done
    server.stop()
    server.join()
