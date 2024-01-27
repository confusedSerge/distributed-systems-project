from ipaddress import IPv4Address

from multiprocessing import Process, Event
from time import sleep

from communication import (
    Multicast,
    Unicast,
    MessageSchema,
    MessageFindReplicaRequest,
    MessageFindReplicaResponse,
    MessageFindReplicaAcknowledgement,
    MessagePeersAnnouncement,
    AuctionMessageData,
    MessageAuctionInformationResponse,
    MessageAuctionInformationAcknowledgement,
)

from model import Auction, AuctionPeersStore
from constant import (
    communication as com,
    BUFFER_SIZE,
    TIMEOUT_REPLICATION,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    MULTICAST_AUCTION_PORT,
    REPLICA_AUCTION_POOL_SIZE,
)

from util import create_logger, logger, Timeout, generate_message_id


class ReplicaFinder(Process):
    """Handles the finding of replicas for an auction.

    The replica finder process runs in the background as follows:
    - Sends a find replica request to the discovery multicast group.
    - Receives find replica responses from the default unicast port.
    - Sends a find replica acknowledgement to the response sender.
    - Adds the response sender to the replica list.
    - Repeats until the replica list is full.

    The replica request is send periodically until the replica list is full.
    """

    def __init__(
        self,
        auction: Auction,
        auction_peers_store: AuctionPeersStore,
        emitter_period: int = 60,
    ):
        """Initializes the replica finder process.

        Args:
            auction (Auction): The auction to find replicas for. Should be a shared memory object.
            auction_peers_store (list): The list to add the replicas to. Should be a shared memory object. Can be non-empty, representing already found replicas.
            emitter_period (int, optional): The period of the replica request emitter. Defaults to 60 seconds.
        """
        super(ReplicaFinder, self).__init__()
        self._exit: Event = Event()

        self._name: str = f"ReplicaFinder::{auction.get_id()}"
        self._logger: logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        self._peers: AuctionPeersStore = auction_peers_store
        self._emitter_period: int = emitter_period

        self._logger.info(f"{self._name}: Initialized")

    def run(self):
        """Runs the replica finder process."""
        self._logger.info(f"{self._name}: Started")
        uc: Unicast = Unicast()

        # Start replica request emitter
        self._logger.info(f"{self._name}: Starting replica request emitter")
        message_id: str = generate_message_id(self._auction.get_id())
        emitter: Process = Process(
            target=self._emit_request,
            args=(
                message_id,
                uc.get_address(),
            ),
        )
        emitter.start()

        try:
            new_replicas: list[tuple[IPv4Address, int]] = self._find_replicas(
                uc, message_id
            )
        except TimeoutError:
            self._logger.info(f"{self._name}: Not enough replicas found; Exiting")
            uc.close()
            return
        finally:
            if emitter.is_alive():
                emitter.terminate()
                emitter.join()

        # Add new replica to known replicas
        try:
            self._peers.append(new_replicas)
        except ValueError:
            self._logger.info(f"{self._name}: Duplicate replica found; Exiting")
            return

        if self._exit.is_set():
            self._logger.info(
                f"{self._name}: Received stop signal during replica finding: Exiting"
            )
            return

        self._logger.info(f"{self._name}: Found enough replicas")

        self._send_information(uc, message_id, new_replicas)
        sleep(5)  # TODO: Remove
        self._announce_replica(message_id)

        self._logger.info(f"{self._name}: Releasing resources")

    def stop(self):
        """Stops the replica finder process."""
        self._logger.info(f"{self._name} received stop signal")
        self._exit.set()

    def _find_replicas(
        self, uc: Unicast, message_id: str
    ) -> list[tuple[IPv4Address, int]]:
        """Finds replicas for the auction.

        Args:
            uc (Unicast): The unicast socket.
            message_id (str): The message id to use for the find replica request.

        Returns:
            list[tuple[IPv4Address, int]]: The list of new replicas.
        """
        seen_addresses: list[tuple[IPv4Address, int]] = []
        new_replicas: list[tuple[IPv4Address, int]] = []

        acknowledgement: bytes = MessageFindReplicaAcknowledgement(
            _id=message_id
        ).encode()

        self._logger.info(f"{self._name}: Finding replicas")
        with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
            while (
                self._peers.len() + len(new_replicas) < REPLICA_AUCTION_POOL_SIZE
                and not self._exit.is_set()
            ):
                # Receive find replica response
                response, address = uc.receive(BUFFER_SIZE)

                if not MessageSchema.of(com.HEADER_FIND_REPLICA_RES, response):
                    continue

                response: MessageFindReplicaResponse = (
                    MessageFindReplicaResponse.decode(response)
                )

                if address in seen_addresses:
                    self._logger.info(
                        f"{self._name}: Received duplicate find replica response {response} from {address}"
                    )
                    continue

                if response._id != message_id:
                    self._logger.info(
                        f"{self._name}: Received find replica response {response} from {address} with invalid message id {response._id}"
                    )
                    continue

                self._logger.info(
                    f"{self._name}: Received find replica response {response} from {address}"
                )

                # Send find replica acknowledgement
                uc.send(acknowledgement, address)
                self._logger.info(
                    f"{self._name}: Acknowledged sent to {address} for find replica response {response}"
                )

                # Add replica to list
                new_replicas.append(address)
                seen_addresses.append(address)

        return new_replicas

    def _send_information(
        self, uc: Unicast, message_id: str, new_replicas: list[IPv4Address]
    ) -> None:
        """Sends auction information to new replicas and replica announcement to all replicas.

        Args:
            uc (Unicast): The unicast socket.
            message_id (str): The message id to use for the messages.
            new_replicas (list[IPv4Address]): The list of new replicas.
        """
        # Send Auction Information to new replicas
        self._logger.info(f"{self._name}: Sending auction information to new replicas")
        response = MessageAuctionInformationResponse(
            _id=message_id,
            auction=AuctionMessageData.from_auction(self._auction),
            port=uc.get_address(),
        )
        for replica in new_replicas:
            self._logger.info(f"{self._name}: Sending auction information to {replica}")
            uc.send(response.encode(), replica)

            try:
                # TODO: Other timeout?
                with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
                    while not self._exit.is_set():
                        acknowledgement, address = uc.receive(BUFFER_SIZE)

                        if not MessageSchema.of(
                            com.HEADER_AUCTION_INFORMATION_ACK, acknowledgement
                        ):
                            continue
                        acknowledgement: MessageAuctionInformationAcknowledgement = (
                            MessageAuctionInformationAcknowledgement.decode(
                                acknowledgement
                            )
                        )

                        if address[0] != str(replica[0]):
                            self._logger.info(
                                f"{self._name}: Received auction information acknowledgement {acknowledgement} from {address} instead of {replica}"
                            )
                            continue

                        if acknowledgement._id != message_id:
                            self._logger.info(
                                f"{self._name}: Received auction information acknowledgement {acknowledgement} with invalid message id {acknowledgement._id}"
                            )
                            continue

                        self._logger.info(
                            f"{self._name}: Received auction information acknowledgement {acknowledgement} from {address}"
                        )

                        break
            except TimeoutError:
                self._logger.info(
                    f"{self._name}: Did not receive auction information acknowledgement from {replica}"
                )
                self._logger.info(f"{self._name}: Stopping replica finding")
                self.stop()
                return

            self._logger.info(
                f"{self._name}: Received auction information acknowledgement from all replicas"
            )

    def _announce_replica(self, message_id: str) -> None:
        """Announces the replica to all other replicas.

        Args:
            message_id (str): The message id to use for the message.
        """
        self._logger.info(
            f"{self._name}: Announcing replica to all replicas at {(self._auction.get_address(), MULTICAST_AUCTION_PORT)} with message id {message_id}"
        )
        peers: MessagePeersAnnouncement = MessagePeersAnnouncement(
            _id=message_id,
            peers=[(str(peer[0]), peer[1]) for peer in self._peers.iter()],
        )
        Multicast.qsend(
            message=peers.encode(),
            group=self._auction.get_address(),
            port=MULTICAST_AUCTION_PORT,
        )

    def _emit_request(self, message_id: str, uc_port: int) -> None:
        """Sends a find replica request periodically.

        Args:
            message_id (str): The message id to use for the find replica request.
        """
        mc: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP, port=MULTICAST_DISCOVERY_PORT, sender=True
        )
        req: bytes = MessageFindReplicaRequest(
            _id=message_id,
            # TODO: THIS IS WRONG
            address=str(self._auction.get_address()),
            port=uc_port,
        ).encode()

        while not self._exit.is_set():
            mc.send(req)
            self._logger.info(f"{self._name}: Emitter: Sent find replica request")
            sleep(self._emitter_period)

        mc.close()
        self._logger.info(f"{self._name}: Emitter: Stopped")
