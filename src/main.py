from client import Client
from server import Server

from multiprocessing import Process
from ipaddress import IPv4Address
from communication import ReliableUnicast
from constant import REPLICA_ELECTION_PORT


# def send(address: tuple[IPv4Address, int]) -> None:
#     """Send a message to the server."""
#     unicast = ReliableUnicast()
#     print(f"Sending message to {address}")
#     unicast.send(b"Hello, server", address)


if __name__ == "__main__":

    # unicast = ReliableUnicast(port=REPLICA_ELECTION_PORT, timeout=10)
    # sender = Process(target=send, args=(unicast.get_address(),))
    # sender.start()

    # message, address = unicast.receive()
    # print(f"Received message: {message} from {address}")

    client = Client()
    server = Server()

    # Start background processes
    server.start()
    client.run()

    # Terminate client and server processes when client interaction is done
    server.stop()
    server.join()
