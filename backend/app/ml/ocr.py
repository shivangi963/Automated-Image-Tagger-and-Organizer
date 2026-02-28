"""
OCR extractor using EasyOCR.
Detects and extracts printed / handwritten text from images.
Useful for signs, labels, documents, memes, screenshots, etc.
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OCRExtractor:
    """
    Lazy-loading EasyOCR wrapper.
    Model downloads ~200 MB on first use.
    """

    def __init__(self, languages: List[str] = None):
        self._reader = None
        self._languages = languages or ["en"]

    def _load_reader(self):
        if self._reader is not None:
            return
        try:
            import easyocr
            logger.info(
                f"Loading EasyOCR for languages {self._languages} "
                "(first run downloads ~200 MB)…"
            )
            # gpu=False keeps things predictable inside Celery workers;
            # set gpu=True if you have CUDA available and want faster OCR.
            self._reader = easyocr.Reader(self._languages, gpu=False)
            logger.info("✓ EasyOCR loaded")
        except Exception as e:
            logger.error(f"Failed to load EasyOCR: {e}")
            raise

    def extract_text(self, image_path: str, min_confidence: float = 0.3) -> Dict:
        """
        Run OCR on an image file.

        Returns:
            {
                "full_text": "concatenated text",
                "regions": [
                    {
                        "text": str,
                        "confidence": float,
                        "bbox": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                    },
                    ...
                ],
                "has_text": bool
            }
        """
        self._load_reader()

        try:
            raw = self._reader.readtext(image_path)
        except Exception as e:
            logger.error(f"EasyOCR readtext failed: {e}")
            return {"full_text": "", "regions": [], "has_text": False}

        regions = []
        for bbox, text, confidence in raw:
            text = text.strip()
            if not text or confidence < min_confidence:
                continue
            regions.append(
                {
                    "text": text,
                    "confidence": round(float(confidence), 4),
                    # bbox is a list of 4 [x, y] points — JSON-serialisable
                    "bbox": [[int(p[0]), int(p[1])] for p in bbox],
                }
            )

        full_text = " ".join(r["text"] for r in regions)

        logger.info(
            f"OCR found {len(regions)} text region(s): "
            f"{full_text[:80]}{'…' if len(full_text) > 80 else ''}"
        )

        return {
            "full_text": full_text,
            "regions": regions,
            "has_text": bool(regions),
        }


# Module-level singleton
ocr_extractor = OCRExtractor(languages=["en"])