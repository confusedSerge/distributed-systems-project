from marshmallow import Schema, fields, EXCLUDE


class MessageSchema(Schema):
    """MessageSchema class for marshmallow serialization."""

    _id = fields.String(required=True)
    tag = fields.String(required=True)

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
        return MessageSchema.decode(message)["tag"] == header

    @staticmethod
    def decode(message: bytes) -> dict:
        """Return the decoded message

        Args:
            message (bytes): The message to decode.

        Returns:
            dict: The decoded message containing the tag and id.
        """
        return MessageSchema(partial=True).loads(message)
