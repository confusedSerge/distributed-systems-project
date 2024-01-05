"""This module contains functions for certain processes, which are common to both the client and the server."""

from model import Auction
from constant import addresses

import message as msgs
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
    request = msgs.FindReplicaRequest(
        _id=auction._id,
        auction_multicast_group=auction.multicast_group,
        auction_multicast_port=auction.multicast_port,
    )

    # Create a multicast sender to send find replica requests
    multicast_sender = Multicast(
        addresses.MULTICAST_DISCOVERY_GROUP, addresses.MULTICAST_DISCOVERY_PORT
    )
    # Create unicasts to receive find replica responses
    respone_listener = Unicast("", addresses.UNICAST_DISCOVERY_PORT, sender=False)

    # Send find replica requests
    multicast_sender.send(request.encode())

    while len(replicas_list) < number_of_replicas:
        # Receive find replica responses
        response, address = respone_listener.receive()
        decoded_response = msgs.decode(response)

        if decoded_response["tag"] != msgs.message.FIND_REPLICA_RESPONSE_TAG:
            continue

        # Decode find replica response
        decoded_response = msgs.FindReplicaResponse.decode(response)

        if decoded_response._id != auction._id:
            continue

        # Add replica to list
        replicas_list.append(address)

    # Release List of replicas to all replicas through multicast
    release_message = msgs.AuctionReplicaPeers(
        _id=auction._id,
        peers=replicas_list,
    )
    multicast_sender.send(release_message.encode())

    # Close multicast sender and unicast listener
    multicast_sender.close()
    respone_listener.close()
