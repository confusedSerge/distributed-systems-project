from util import Multicast, FindReplicaRequest
from constant import multicast as constant_multicast

from multiprocessing import Process

from client import Client
from server import Server

sender = Multicast(
    constant_multicast.MULTICAST_DISCOVERY_GROUP,
    constant_multicast.MULTICAST_DISCOVERY_PORT,
    sender=True,
    ttl=constant_multicast.MULTICAST_DISCOVERY_TTL,
)
receiver = Multicast(
    constant_multicast.MULTICAST_DISCOVERY_GROUP,
    constant_multicast.MULTICAST_DISCOVERY_PORT,
    sender=False,
    ttl=constant_multicast.MULTICAST_DISCOVERY_TTL,
)


def send():
    message: FindReplicaRequest = FindReplicaRequest(data="Hello, world!")

    sender.send(message.encode())

    print("Sent message:", message)

    sender.close()


def receive():
    message, address = receiver.receive()

    print("Received message:", FindReplicaRequest.decode(message), " from ", address)

    receiver.close()


if __name__ == "__main__":
    # Create server process
    server = Server()
    server_process = Process(target=server.run)

    # Create client process
    client = Client()
    client_process = Process(target=client.run)

    # Start background processes
    server_process.start()
    client_process.start()

    # Interact with client
    client.interact()

    # Terminate client and server processes when client interaction is done
    server_process.terminate()
    client_process.terminate()
