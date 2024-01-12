from client import Client
from server import Server

from multiprocessing import Process
from communication import Unicast


def send_message() -> None:
    """Sends a message to the server."""
    message: str = "Hello World!"
    print(f"Sending message: {message}")

    Unicast.qsend(
        message=message.encode(),
        host="0.0.0.0",
        port=5000,
    )


def receive_message(_id: int) -> None:
    """Receives a message from the server."""
    uc = Unicast(host=None, port=5000)
    message, address = uc.receive(1024)
    print(f"{_id} Received message: {message.decode()} from {address[0]}:{address[1]}")


if __name__ == "__main__":
    sender = Process(target=send_message)
    rec1 = Process(target=receive_message, args=(1,))
    rec2 = Process(target=receive_message, args=(2,))
    rec3 = Process(target=receive_message, args=(3,))

    rec1.start()
    rec2.start()
    rec3.start()
    sender.start()

    # client = Client()
    # server = Server()

    # # Start background processes
    # client.start()
    # server.start()

    # # Interact with client
    # client.interact()

    # # Terminate client and server processes when client interaction is done
    # client.stop()
    # server.stop()
