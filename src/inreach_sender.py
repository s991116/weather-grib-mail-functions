from typing import Protocol
import httpx

class InReachSender(Protocol):
    """
    Protocol for sending a single InReach message.
    """

    async def __call__(
        self,
        client: httpx.AsyncClient,
        url: str,
        message: str,
    ) -> httpx.Response:
        ...
