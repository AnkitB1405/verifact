"""Input processing: validate, normalise, split into sentences.

Owner: P2. Contract produced: `Document`.
"""

from verifact.input.processor import build_document, normalize_text, split_sentences

__all__ = ["build_document", "normalize_text", "split_sentences"]
