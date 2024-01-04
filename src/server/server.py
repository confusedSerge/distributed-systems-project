class Server:
    """Server class

    This class is responsible for creating the backbone of the auction system.
    It handles the following:
        - Listening for replica requests (discovery group) and creating replicas for them, if there is enough space in the pool.
    """
