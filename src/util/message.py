from typing import Self

from dataclasses import dataclass, field
import marshmallow_dataclass

from json import dumps, loads

import constant.message


@dataclass
class FindReplicaRequest:
    """FindReplicaRequest class for sending and receiving find new replica requests."""

    # TODO: Find a way to make this a constant
    tag: str = field(default=constant.message.FIND_REPLICA_REQUEST_TAG)
    data: str = field(default="")

    def __str__(self) -> str:
        """Return the string representation of the find new replica request."""
        return f"FindNewReplicaRequest(tag={self.tag}, data={self.data})"

    def __repr__(self) -> str:
        """Return the string representation of the find new replica request."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Return whether the find new replica request is equal to another find new replica request."""
        if not isinstance(o, FindReplicaRequest):
            return False
        return self.tag == o.tag and self.data == o.data

    def __hash__(self) -> int:
        """Return the hash of the find new replica request."""
        return hash((self.tag, self.data))

    def encode(self) -> bytes:
        """Return the encoded find new replica request."""
        return bytes(dumps(FIND_REPLICA_REQUEST_SCHEMA().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded find new replica request."""
        return FIND_REPLICA_REQUEST_SCHEMA().load(loads(message))

@dataclass
class Message:
    """Message clas to send messages"""
    def __init__(self, message_content: bytes, message_id: int, sender_ip: str):
        self.message_content = message_content
        self.message_id = message_id
        self.sender_ip = sender_ip


FIND_REPLICA_REQUEST_SCHEMA = marshmallow_dataclass.class_schema(FindReplicaRequest)
