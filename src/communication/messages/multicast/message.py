from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from constant import HEADER_ISIS_MESSAGE


@dataclass
class MessageIsisMessage:
    """Initial ISIS message."""
