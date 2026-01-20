from dataclasses import dataclass
from typing import Literal

@dataclass
class InReachRequest:
    type: Literal["weather", "chat"]
    payload_text: str
    reply_url: str

