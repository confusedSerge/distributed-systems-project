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

from communication import ReliableUnicast, MessageElectionRequest
from multiprocessing import Process
from util import generate_message_id


def send_election_request(address: tuple[IPv4Address, int]) -> None:
    election_request = MessageElectionRequest(
        _id=generate_message_id(),
        req_id=(str(IPv4Address("192.168.0.100")), 5555),
    )
    unicast = ReliableUnicast()
    try:
        unicast.send(election_request.encode(), address)
    except TimeoutError:
        print("Election request not sent reliably")
        return
    print("Election request sent reliably")


if __name__ == "__main__":

    unicast = ReliableUnicast()
    address = unicast.get_address()

    # Start sending election request
    sender = Process(target=send_election_request, args=(address,))
    # sender.start()

    # Start listening for election request
    try:
        message, from_address = unicast.receive()
        print(
            f"Election request {MessageElectionRequest.decode(message)} received from {from_address}"
        )
    except TimeoutError:
        print("Election request not received")

    # sender.join()

    # new_peers = [
    #     (IPv4Address("192.168.0.100"), 5555),
    #     (IPv4Address("192.168.0.102"), 6666),
    #     (IPv4Address("192.168.0.100"), 7777),
    # ]

    # sorted_peers = sorted(new_peers)
    # print(sorted_peers)

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
