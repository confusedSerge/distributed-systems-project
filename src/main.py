from ipaddress import IPv4Address
from multiprocessing import Event
from client import Client
from constant.communication.multicast import DISCOVERY_GROUP
from model import auction
from model.auction_peers_store import AuctionPeersStore
from process.listener.auction_peers_announcement_listener import (
    AuctionPeersAnnouncementListener,
)
from process.memory_manager import Manager
from server import Server


if __name__ == "__main__":

    new_peers = [
        (IPv4Address("192.168.0.100"), 5555),
        (IPv4Address("192.168.0.102"), 6666),
        (IPv4Address("192.168.0.100"), 7777),
    ]

    sorted_peers = sorted(new_peers)
    print(sorted_peers)

    # client = Client()
    # server = Server()

    # # Start background processes
    # server.start()
    # client.run()

    # # Terminate client and server processes when client interaction is done
    # server.stop()
    # server.join()

    # new_peers = [("0.0.0.0", 5555), ("0.0.0.0", 6666), ("0.0.0.0", 7777)]

    # manager = Manager()
    # manager.start()

    # store = manager.AuctionPeersStore()  # type: ignore
    # auction = manager.Auction("a", "a", "a", 0.0, 10, DISCOVERY_GROUP)  # type: ignore
    # listener = AuctionPeersAnnouncementListener(auction, store, Event())
    # listener.start()
    # listener.join()
