from ipaddress import IPv4Address, IPv4Network
from uuid import uuid4

from random import choice

from constant import communication as com
from constant.account import USERNAME


def generate_mc_address(known_addresses: list[IPv4Address]) -> IPv4Address:
    """Generate a unique multicast address not in use, based on the list of known used multicast addresses.

    Args:
        known_addresses (list[IPv4Address]): The list of known in use multicast addresses.

    Returns:
        IPv4Address: The unique multicast address.
    """
    base_network: IPv4Network = com.MULTICAST_AUCTION_GROUP_BASE
    unused_addresses: list[IPv4Address] = [
        addr for addr in base_network.hosts() if addr not in known_addresses
    ]

    return choice(unused_addresses)


def generate_message_id(auction: str = "") -> str:
    """Generates a unique message id.

    If auction is not empty, the auction id is also included in the message id.
    The resulting message id is of the form "uname::uuid" or "uname::aname::uuid".

    The provided auction id should be of the form "uname::aname".

    Args:
        auction (str, optional): The auction id. Defaults to "".

    Returns:
        str: The unique message id.
    """
    return f"{auction}::{uuid4()}" if auction else f"{USERNAME}::{uuid4()}"
