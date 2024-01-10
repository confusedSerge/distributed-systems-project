from ipaddress import IPv4Address

from constant import communication as com


def generate_unique_mc_address(
    known_addresses: list[tuple[IPv4Address, int]]
) -> tuple[str, int]:
    """Generate a unique multicast address.

    Args:
        known_addresses (list[tuple[IPv4Address, int]]): The list of known in use multicast addresses.

    Returns:
        tuple[IPv4Address, int]: The unique multicast address.
    """
    pass
