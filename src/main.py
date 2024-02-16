from client import Client
from server import Server

from multiprocessing import Process
from ipaddress import IPv4Address
from communication import ReliableUnicast
from constant import REPLICA_ELECTION_PORTS


if __name__ == "__main__":

    client = Client()
    server = Server()

    # Start background processes
    server.start()
    client.run()

    # Terminate client and server processes when client interaction is done
    server.terminate()
    server.join()
