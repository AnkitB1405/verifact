"""Claim extraction. Owner: P2. Contract produced: `list[Claim]`."""

from verifact.extraction.checkworthy import classify
from verifact.extraction.decompose import decompose, is_standalone_interpretable
from verifact.extraction.extractor import extract_claims

__all__ = ["classify", "decompose", "extract_claims", "is_standalone_interpretable"]
