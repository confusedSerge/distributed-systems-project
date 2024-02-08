from client import Client
from server import Server

from communication import IsisRMulticast
from ipaddress import IPv4Address
from constant import MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT


def send():
    multicast = IsisRMulticast(
        IPv4Address(MULTICAST_DISCOVERY_GROUP), MULTICAST_DISCOVERY_PORT
    )
    multicast.send(b"Hello, world!")
    print(multicast.deliver())
    multicast.close()


def receive():
    multicast = IsisRMulticast(
        IPv4Address(MULTICAST_DISCOVERY_GROUP), MULTICAST_DISCOVERY_PORT, 30
    )
    print(multicast.deliver())
    multicast.send(b"Hello, back!")
    multicast.close()


if __name__ == "__main__":

    # receive()
    send()
    # client = Client()
    # server = Server()

    # # Start background processes
    # server.start()
    # client.run()

    # # Terminate client and server processes when client interaction is done
    # server.stop()
    # server.join()
