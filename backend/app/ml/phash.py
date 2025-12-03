import imagehash
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def compute_phash(image_path: str, hash_size: int = 8) -> str:
    """
    Compute perceptual hash of an image
    
    Args:
        image_path: Path to image file
        hash_size: Hash size (default 8 for 64-bit hash)
    
    Returns:
        Hexadecimal string representation of hash
    """
    try:
        image = Image.open(image_path)
        phash = imagehash.phash(image, hash_size=hash_size)
        return str(phash)
    except Exception as e:
        logger.error(f"Error computing pHash: {e}")
        return None


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance between two hashes
    
    Args:
        hash1: First hash string
        hash2: Second hash string
    
    Returns:
        Hamming distance (number of differing bits)
    """
    try:
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2
    except Exception as e:
        logger.error(f"Error calculating Hamming distance: {e}")
        return 999  # Return high value on error


def are_duplicates(hash1: str, hash2: str, threshold: int = 8) -> bool:
    """
    Check if two images are likely duplicates based on pHash
    
    Args:
        hash1: First hash string
        hash2: Second hash string
        threshold: Maximum Hamming distance for duplicates (default 8)
    
    Returns:
        True if images are likely duplicates
    """
    distance = hamming_distance(hash1, hash2)
    return distance <= threshold


def similarity_score(hash1: str, hash2: str) -> float:
    """
    Calculate similarity score between two images (0-1)
    
    Args:
        hash1: First hash string
        hash2: Second hash string
    
    Returns:
        Similarity score (1 = identical, 0 = completely different)
    """
    distance = hamming_distance(hash1, hash2)
    max_distance = 64  # For 8x8 hash
    return 1 - (distance / max_distance)