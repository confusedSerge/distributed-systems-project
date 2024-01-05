from multiprocessing import Process

from util.helper import load_config

from client import Client
from server import Server


if __name__ == "__main__":
    # Load configuration
    config = load_config()

    client = Client(config=config)

    # Start background processes
    client.start()

    # Interact with client
    client.interact()

    # Terminate client and server processes when client interaction is done
    client.stop()

# from util import Multicast, AuctionReplicaPeers, MessageSchema
# from constant import message, addresses

# sender = Multicast(
#     addresses.MULTICAST_DISCOVERY_GROUP,
#     addresses.MULTICAST_DISCOVERY_PORT,
#     sender=True,
#     ttl=addresses.MULTICAST_DISCOVERY_TTL,
# )
# receiver = Multicast(
#     addresses.MULTICAST_DISCOVERY_GROUP,
#     addresses.MULTICAST_DISCOVERY_PORT,
#     sender=False,
#     ttl=addresses.MULTICAST_DISCOVERY_TTL,
# )


# def send():
#     message: AuctionReplicaPeers = AuctionReplicaPeers(
#         _id=1,
#         peers=[("192.168.0.0", 5000), ("192.168.0.1", 5001)],
#     )

#     sender.send(message.encode())

#     print("Sent message:", message)

#     sender.close()


# def receive():
#     rcm, rca = receiver.receive()
#     print("Received message:", rcm, " from ", rca)

#     dcm = MessageSchema(partial=True).loads(rcm)
#     print("Decoded message:", dcm)

#     if dcm["tag"] == message.AUCTION_REPLICA_PEERS_TAG:
#         dcm = AuctionReplicaPeers.decode(rcm)
#         print("Decoded message:", dcm)
#     else:
#         print(f"Message is not a find replica request. (tag={dcm.tag})")

#     receiver.close()


# if __name__ == "__main__":
#     send_process = Process(target=send)
#     receive_process = Process(target=receive)

#     send_process.start()
#     receive_process.start()

#     send_process.join()
#     receive_process.join()
