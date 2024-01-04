class Client:
    """Client class for the client side of the peer-to-peer network.

    The client class runs in a separate thread (process) from the server class.
    It handles the two cases of client actions; auctioneering and bidding implemented in their respective classes.

    The client actions are given through an interactive command line interface, which will cause to run the respective methods.
    """
