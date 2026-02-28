"""
Perceptual hashing for duplicate image detection.
Uses imagehash library — pHash is robust against:
  - resizing / compression
  - minor colour adjustments
  - JPEG re-encoding artefacts

Two images with a Hamming distance <= 10 are considered near-duplicates.
"""
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# Hamming-distance threshold for declaring two images "duplicates"
DUPLICATE_THRESHOLD = 10


def compute_phash(image_path: str) -> Optional[str]:
    """
    Compute the perceptual hash (pHash) of an image file.

    Returns the hash as a hex string (e.g. "a3f2b1c4..."),
    or None if the image cannot be processed.
    """
    try:
        import imagehash
        from PIL import Image

        img = Image.open(image_path).convert("RGB")
        h = imagehash.phash(img)
        return str(h)
    except Exception as e:
        logger.error(f"pHash computation failed for {image_path}: {e}")
        return None


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Compute the Hamming distance between two pHash hex strings.
    Lower = more similar.  0 = identical.
    """
    try:
        import imagehash
        return imagehash.hex_to_hash(hash1) - imagehash.hex_to_hash(hash2)
    except Exception as e:
        logger.error(f"Hamming distance error: {e}")
        return 999  # treat as completely different on error


def are_duplicates(hash1: str, hash2: str, threshold: int = DUPLICATE_THRESHOLD) -> bool:
    """Return True if two images are near-duplicates."""
    return hamming_distance(hash1, hash2) <= threshold


def find_duplicates(image_hashes: List[Tuple[str, str]]) -> List[List[str]]:
    """
    Given a list of (image_id, phash_hex) tuples, return groups of duplicate
    image_ids.

    Example:
        find_duplicates([("id1", "abc..."), ("id2", "abc..."), ("id3", "xyz...")])
        → [["id1", "id2"]]   # id3 is unique

    O(n²) — fine for small libraries; switch to LSH for 100k+ images.
    """
    n = len(image_hashes)
    visited = [False] * n
    groups = []

    for i in range(n):
        if visited[i]:
            continue
        img_id_i, hash_i = image_hashes[i]
        group = [img_id_i]

        for j in range(i + 1, n):
            if visited[j]:
                continue
            img_id_j, hash_j = image_hashes[j]
            if are_duplicates(hash_i, hash_j):
                group.append(img_id_j)
                visited[j] = True

        if len(group) > 1:
            visited[i] = True
            groups.append(group)

    return groups