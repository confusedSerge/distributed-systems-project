from multiprocessing import Process

from client import Client
from server import Server

import time
from util import Timeout, TimeoutError


def test():
    try:
        with Timeout(5, throw_exception=True):
            while True:
                print("Background process going strong")
                time.sleep(7)
    except TimeoutError:
        print("Background process timed out")


if __name__ == "__main__":
    start = time.time()
    # Timeout test
    proc = Process(target=test)
    proc.start()
    while proc.is_alive():
        print("Main process going strong")
        time.sleep(10)
    proc.join()

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
