"""Source clients. Owner: P3. All outbound access goes through `SafeClient`."""

from verifact.retrieval.clients.http import SafeClient

__all__ = ["SafeClient"]
