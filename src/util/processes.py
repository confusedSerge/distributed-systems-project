"""This module contains functions for certain processes, which are common to both the client and the server."""

from model import Auction
from constant import addresses as addr, message as msgs_tag, auction as auc_state

from .message import FindReplicaRequest, FindReplicaResponse, AuctionBid, decode
from .multicast import Multicast
from .unicast import Unicast


def find_replicas(
    auction: Auction,
    replicas_list: list,
    number_of_replicas: int,
) -> None:
    """Finds the replicas for an auction.

    Args:
        auction (Auction): The auction to find replicas for.
        replicas_list (list): Callback list for the replicas.
        number_of_replicas (int): The number of replicas to find.
    """
    # Create request
    mc_auc_group, mc_auc_port = auction.get_multicast_group_port()
    request = FindReplicaRequest(
        _id=auction._id,
        auction_multicast_group=mc_auc_group,
        auction_multicast_port=mc_auc_port,
    )

    # Create a multicast sender to send find replica requests
    multicast_sender = Multicast(
        addr.MULTICAST_DISCOVERY_GROUP, addr.MULTICAST_DISCOVERY_PORT
    )
    # Create unicasts to receive find replica responses
    respone_listener = Unicast("", addr.UNICAST_DISCOVERY_PORT, sender=False)

    # Send find replica requests
    multicast_sender.send(request.encode())

    while len(replicas_list) < number_of_replicas:
        # Receive find replica responses
        response, address = respone_listener.receive()
        decoded_response = decode(response)

        if decoded_response["tag"] != msgs_tag.FIND_REPLICA_RESPONSE_TAG:
            continue

        # Decode find replica response
        decoded_response: FindReplicaResponse = FindReplicaResponse.decode(response)

        if decoded_response._id != auction._id:
            continue

        # Add replica to list
        replicas_list.append(address)

    # Close multicast sender and unicast listener
    multicast_sender.close()
    respone_listener.close()


def listen_auction(
    auction: Auction,
) -> None:
    """Listens to an auction.

    Args:
        auction (Auction): The auction to listen to.
    """
    # Create a multicast listener to receive bids
    mc_auc_group, mc_auc_port = auction.get_multicast_group_port()
    multicast_listener = Multicast(mc_auc_group, mc_auc_port, sender=False)

    while auction.get_state() != auc_state.AUCTION_ENDED:
        # Receive bids
        bid, _ = multicast_listener.receive()
        decoded_bid = decode(bid)

        if decoded_bid["tag"] == msgs_tag.AUCTION_BID_TAG:
            decoded_bid: AuctionBid = AuctionBid.decode(bid)
            if auction.get_id() != decoded_bid.auction_id:
                continue

            # Add bid to auction
            auction.bid(decoded_bid.bidder, decoded_bid.bid)

        # TODO: Check if message is auction end message

    # Close multicast listener
    multicast_listener.close()
