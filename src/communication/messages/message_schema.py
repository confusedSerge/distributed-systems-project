from marshmallow import Schema, fields, EXCLUDE

from json import loads


class MessageSchema(Schema):
    """MessageSchema class for marshmallow de/serialization.

    Fields:
        _id (str): The unique identifier of the message. This depends on the message type.
            General structure is "uname::uuid", such that the message can be uniquely identified by the sender.
            Depending on an auction, the message ID is then "uname::aname::uuid", such that the message can be uniquely identified by the corresponding auction.
        header (str): The header of the message.
    """

    _id = fields.String(required=True)
    header = fields.String(required=True)

    class Meta:
        unknown = EXCLUDE

    @staticmethod
    def of(header: str, message: bytes) -> bool:
        """Return whether the message is of the given message type.

        Args:
            header (str): The header for a given message type.
            message (bytes): The message to check.

        Returns:
            bool: Whether the message is of the given header type.
        """
        return MessageSchema.decode(message)["header"] == header

    @staticmethod
    def get_id(message: bytes) -> str:
        """Return the message id.

        Args:
            message (bytes): The message to get the id from.

        Returns:
            str: The message id.
        """
        return MessageSchema.decode(message)["_id"]

    @staticmethod
    def decode(message: bytes) -> dict:
        """Return the decoded message

        Args:
            message (bytes): The message to decode.

        Returns:
            dict: The decoded message containing the tag and id.
        """
        return MessageSchema(partial=True).loads(loads(message))  # type: ignore
