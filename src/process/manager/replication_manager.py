from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event
from time import sleep

from logging import Logger

# === Custom Modules ===

from communication import (
    Multicast,
    ReliableUnicast,
    MessageSchema,
    MessageFindReplicaRequest,
    MessageFindReplicaResponse,
    MessageAuctionPeersAnnouncement,
    AuctionMessageData,
    MessageAuctionInformationReplication,
)
from model import Auction, AuctionPeersStore
from util import create_logger, generate_message_id, Timeout

from constant import (
    communication as com,
    BUFFER_SIZE,
    TIMEOUT_REPLICATION,
    RELIABLE_TIMEOUT,
    RELIABLE_ATTEMPTS,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    MULTICAST_AUCTION_PORT,
    REPLICA_AUCTION_POOL_SIZE,
)


class ReplicationManager(Process):
    """Handles the finding of replicas for an auction.

    The replica finder process is responsible for finding replicas for an auction and adding them to the list of known replicas.
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
        super(ReplicationManager, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}::{auction.get_id()}"
        self._logger: Logger = create_logger(self._name, with_pid=True)

        # Shared memory objects
        self._auction: Auction = auction
        self._peers: AuctionPeersStore = auction_peers_store

        # Configuration
        self._emitter_period: int = emitter_period

        self._logger.info(f"{self._name}: Initialized")

    def run(self):
        """Runs the replica finder process.

        This is done through the following steps:
            - Start replica request emitter with a new message id and corresponding ReliableUnicast port for responses
            - Find replica candidates for the auction
            - Stop replica request emitter
            - Send auction information to replica candidates and keep track of which replicas acknowledge the auction information
            - Add new replicas to list of known replicas that acknowledge the auction information
            - Announce new list of known replicas of the auction to all replicas
        """

        self._logger.info(f"{self._name}: Started")

        # Initialize ReliableUnicast socket for communication with replicas
        uc: ReliableUnicast = ReliableUnicast(
            timeout=RELIABLE_TIMEOUT, retry=RELIABLE_ATTEMPTS
        )

        # Start replica request emitter
        message_id, emitter = self._start_emitter(uc)

        try:
            new_peer_candidates: list[tuple[IPv4Address, int]] = self._find_replicas(
                message_id, uc
            )
        except TimeoutError:
            self._logger.info(f"{self._name}: Not enough replicas found; Exiting")
            uc.close()
            return
        finally:
            if emitter.is_alive():
                emitter.terminate()
                emitter.join()

        # If exit signal was received during replica finding, exit and do not add new replicas
        # Replicas will time out and exit, as they do not receive an auction information message
        if self._exit.is_set():
            self._logger.info(
                f"{self._name}: Received stop signal during replica finding: Exiting"
            )
            return

        self._logger.info(f"{self._name}: Found enough replicas")

        new_peers: list[tuple[IPv4Address, int]] = self._send_information(
            message_id, uc, new_peer_candidates
        )

        # Add new replica to known replicas that acknowledge the auction information
        try:
            self._peers.append(new_peers)
        except ValueError:
            self._logger.info(f"{self._name}: Duplicate replica found; Exiting")
            return

        sleep(0.01)  # Sleep to allow for shared memory update
        self._announce_peers(message_id)

        self._logger.info(f"{self._name}: Releasing resources")

    def stop(self):
        """Stops the replica finder process."""
        self._logger.info(f"{self._name} received stop signal")
        self._exit.set()

    # === Helper Methods ===

    def _find_replicas(
        self,
        message_id: str,
        uc: ReliableUnicast,
    ) -> list[tuple[IPv4Address, int]]:
        """Finds replicas for the auction.

        The replica finding process is done through the following steps:
            - Receive find replica responses
            - Ignore if message is not a find replica response or if the message is not for this replica finder
            - Send find replica acknowledgement and add replica to list
            - Repeat until enough replicas are found or timeout is reached

        Args:
            uc (ReliableUnicast): The ReliableUnicast socket.
            message_id (str): The message id to use for the find replica request.

        Returns:
            list[tuple[IPv4Address, int]]: The list of new replicas.
        """
        # Initialize list of seen addresses and new replicas
        seen_addresses: list[tuple[IPv4Address, int]] = [
            peer for peer in self._peers.iter()
        ]
        new_replicas: list[tuple[IPv4Address, int]] = []

        self._logger.info(f"{self._name}: Finding replicas")
        with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
            while (
                self._peers.len() + len(new_replicas) < REPLICA_AUCTION_POOL_SIZE
                and not self._exit.is_set()
            ):
                # Receive find replica response
                try:
                    message, address = uc.receive(BUFFER_SIZE)
                except TimeoutError:
                    continue

                # Ignore if message is not a find replica response or if the message is not for this replica finder
                if (
                    not MessageSchema.of(com.HEADER_FIND_REPLICA_RES, message)
                    or MessageSchema.get_id(message) != message_id
                    or address in seen_addresses
                ):
                    continue

                response: MessageFindReplicaResponse = (
                    MessageFindReplicaResponse.decode(message)
                )

                # Send find replica acknowledgement and add replica to list
                self._logger.info(
                    f"{self._name}: Received find replica response {response} from {address}. Adding to list of new replicas."
                )
                new_replicas.append(address)
                seen_addresses.append(address)

        return new_replicas

    def _send_information(
        self,
        message_id: str,
        uc: ReliableUnicast,
        new_peer_candidates: list[tuple[IPv4Address, int]],
    ) -> list[tuple[IPv4Address, int]]:
        """Sends auction information to new replicas and replica announcement to all replicas.

        Follows the following steps:
            - Send auction information to new replicas
            - Wait for auction information acknowledgement from all new replicas
            - Return list of new replicas that acknowledged the auction information

        Args:
            message_id (str): The message id to use for the messages.
            uc (ReliableUnicast): The ReliableUnicast socket.
            new_replicas (list[tuple[IPv4Address, int]]): A list of new replicas candidates.

        Returns:
            list[tuple[IPv4Address, int]]: The list of new replicas that acknowledged the auction information.
        """
        # Send auction information to new replicas
        response = MessageAuctionInformationReplication(
            _id=message_id,
            auction=AuctionMessageData.from_auction(self._auction),
        ).encode()

        self._logger.info(
            f"{self._name}: Sending auction information to all new replicas"
        )

        unresponsive_replicas = []
        for replica in new_peer_candidates:
            try:
                uc.send(response, replica)
            except TimeoutError:
                unresponsive_replicas.append(replica)
                self._logger.info(f"{self._name}: Replica {replica} is unresponsive")
                continue

        cleaned_new_replicas = [
            replica
            for replica in new_peer_candidates
            if replica not in unresponsive_replicas
        ]

        self._logger.info(
            f"{self._name}: Received auction information acknowledgement from all replicas"
        )
        return cleaned_new_replicas

    def _announce_peers(self, message_id: str) -> None:
        """Announces the peers to all replicas on the auction multicast group.

        Args:
            message_id (str): The message id to use for the message.
        """
        self._logger.info(
            f"{self._name}: Announcing peers to all replicas at {(self._auction.get_group(), MULTICAST_AUCTION_PORT)} with message id {message_id}"
        )
        peers: MessageAuctionPeersAnnouncement = MessageAuctionPeersAnnouncement(
            _id=generate_message_id(self._auction.get_id()),
            peers=[(str(peer[0]), peer[1]) for peer in self._peers.iter()],
        )
        Multicast.qsend(
            message=peers.encode(),
            group=self._auction.get_group(),
            port=MULTICAST_AUCTION_PORT,
        )

    # === Emitter ===

    def _start_emitter(self, uc: ReliableUnicast):
        """Starts the replica request emitter.

        Args:
            uc (ReliableUnicast): The ReliableUnicast socket.

        Returns:
            (str, Process): The message id used for the replica request and the replica request emitter process.
        """
        self._logger.info(f"{self._name}: Starting replica request emitter")
        message_id: str = generate_message_id(self._auction.get_id())
        emitter: Process = Process(
            target=self._emitter_process,
            args=(
                message_id,
                uc.get_address()[1],
            ),
        )
        emitter.start()
        return message_id, emitter

    def _emitter_process(self, message_id: str, response_port: int) -> None:
        """Sends a find replica request periodically.

        Args:
            message_id (str): The message id to use for the find replica request.
            response_port (int): The port to send the find replica response to on ReliableUnicast.
        """
        mc: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP, port=MULTICAST_DISCOVERY_PORT, sender=True
        )

        req: bytes = MessageFindReplicaRequest(
            _id=message_id,
            address=str(self._auction.get_group()),
            port=response_port,
        ).encode()

        while not self._exit.is_set():
            mc.send(req)
            self._logger.info(f"{self._name}: Emitter: Sent find replica request")
            sleep(self._emitter_period)

        mc.close()
        self._logger.info(f"{self._name}: Emitter: Stopped")
