from client import Client
from server import Server

from communication import Unicast, Multicast
from constant import MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT

if __name__ == "__main__":
    # client = Client()
    # server = Server()

    # # Start background processes
    # server.start()
    # client.run()

    # # Terminate client and server processes when client interaction is done
    # server.stop()
    # server.join()

    uc = Unicast()
    address = uc.get_address()
    print(address)
    address = f"{str(address[0])},{address[1]}"

    mc = Multicast(MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT, sender=True)
    mc.send(address.encode())
    mc.close()

    response = uc.receive()
    print(response)
