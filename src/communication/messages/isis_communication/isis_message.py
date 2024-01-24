from dataclasses import dataclass

@dataclass
class Message:
    """Message clas to send messages"""
    def __init__(self, message_content: bytes, message_id: int, sender_ip: str):
        self.message_content = message_content
        self.message_id = message_id
        self.sender_ip = sender_ip