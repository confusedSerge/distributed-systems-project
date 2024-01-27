from client import Client
from server import Server

import socket

if __name__ == "__main__":
    # client = Client()
    # server = Server()

    # # Start background processes
    # server.start()
    # client.run()

    # # Terminate client and server processes when client interaction is done
    # server.stop()
    # server.join()

    s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s1.bind(("", 0))
    print(s1.getsockname())

    s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s2.bind(("", 0))
    print(s2.getsockname())

    s1.sendto(b"Hello", s2.getsockname())
    print(s2.recvfrom(1024))

    s2.sendto(b"World", s1.getsockname())
    print(s1.recvfrom(1024))

    s1.close()
    s2.close()
