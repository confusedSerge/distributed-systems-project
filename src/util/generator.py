from ipaddress import IPv4Address
from uuid import uuid4

from constant import communication as com


def generate_mc_address(known_addresses: list[IPv4Address]) -> IPv4Address:
    """Generate a unique multicast address not in use, based on the list of known used multicast addresses.

    # TODO: Implement this function.

    Args:
        known_addresses (list[IPv4Address]): The list of known in use multicast addresses.

    Returns:
        IPv4Address: The unique multicast address.
    """
    pass


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
    return f"{auction}::{uuid4()}" if auction else f"{com.USERNAME}::{uuid4()}"
