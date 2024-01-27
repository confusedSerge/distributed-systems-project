from client import Client
from server import Server

from communication import Unicast, Multicast
from constant import MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT

from ipaddress import IPv4Address

if __name__ == "__main__":
    # client = Client()
    # server = Server()

    # # Start background processes
    # server.start()
    # client.run()

    # # Terminate client and server processes when client interaction is done
    # server.stop()
    # server.join()

    # Example of how to use the Unicast and Multicast classes

    # On one machine
    uc = Unicast()
    address = uc.get_address()
    print(address)
    address = f"{str(address[0])},{address[1]}"

    mc = Multicast(MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT, sender=True)
    mc.send(address.encode())
    mc.close()

    response, address = uc.receive()
    print(f"Received {response.decode()} from {address}")
    uc.send("Hello".encode(), address)

    # On another machine
    uc = Unicast()
    print(uc.get_address())

    mc = Multicast(MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT, sender=False)
    message, address = mc.receive()

    print(f"Received {message.decode()} from Multicast group {address}")
    mc.close()

    address = message.decode().split(",")
    address = (IPv4Address(address[0]), int(address[1]))
    uc.send("Hello".encode(), address)
    response, address = uc.receive()
    print(f"Received {response.decode()} from {address}")
