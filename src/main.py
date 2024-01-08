from multiprocessing import Process

from client import Client
from server import Server

from util import Timeout, TimeoutError
import time

if __name__ == "__main__":
    start = time.time()
    # Timeout test
    with Timeout(2) as t:
        time.sleep(3)

    end = time.time()
    print("Time elapsed:", end - start)

    # client = Client()
    # server = Server()

    # # Start background processes
    # client.start()
    # server.start()

    # # Interact with client
    # client.interact()

    # # Terminate client and server processes when client interaction is done
    # client.stop()
