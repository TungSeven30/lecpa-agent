"""Hashing utilities for file and content deduplication."""

import hashlib
from pathlib import Path


def compute_file_hash(file_path: str | Path, algorithm: str = "sha256") -> str:
    """Compute hash of a file.

    Args:
        file_path: Path to the file to hash
        algorithm: Hash algorithm to use (sha256, md5, etc.)

    Returns:
        Hexadecimal hash string
    """
    hash_func = hashlib.new(algorithm)
    path = Path(file_path)

    with open(path, "rb") as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def compute_text_hash(text: str, algorithm: str = "sha256") -> str:
    """Compute hash of text content.

    Args:
        text: Text content to hash
        algorithm: Hash algorithm to use (sha256, md5, etc.)

    Returns:
        Hexadecimal hash string
    """
    hash_func = hashlib.new(algorithm)
    hash_func.update(text.encode("utf-8"))
    return hash_func.hexdigest()


def compute_bytes_hash(data: bytes, algorithm: str = "sha256") -> str:
    """Compute hash of bytes.

    Args:
        data: Bytes to hash
        algorithm: Hash algorithm to use (sha256, md5, etc.)

    Returns:
        Hexadecimal hash string
    """
    hash_func = hashlib.new(algorithm)
    hash_func.update(data)
    return hash_func.hexdigest()
