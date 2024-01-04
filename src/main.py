from util import Multicast, FindReplicaRequest
from constant import multicast as constant_multicast

from multiprocessing import Process

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
    send_process = Process(target=send)
    receive_process = Process(target=receive)

    receive_process.start()
    send_process.start()

    send_process.join()
    receive_process.join()
