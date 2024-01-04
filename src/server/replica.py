class Replica:
    """Replica class.

    Each replica is assigned to a specific auction and is responsible for keeping track of the auction.
    One replica is the leader replica, which is responsible for handling the auction, including keeping a heartbeat of other replicas and finding new replicas.
    The other replicas are followers, which are responsible for keeping a heartbeat of the leader replica. If the leader replica fails, a new leader replica is elected.
    In the background, each replica updates its own state on update requests (new bids).
    """
