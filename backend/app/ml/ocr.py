import logging
import os
import tempfile
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OCRExtractor:

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
            self._reader = easyocr.Reader(self._languages, gpu=False)
            logger.info("✓ EasyOCR loaded")
        except Exception as e:
            logger.error(f"Failed to load EasyOCR: {e}")
            raise

    def _preprocess_for_ocr(self, image_path: str) -> Optional[str]:
        """
        Preprocess image to improve OCR accuracy on printed/document text.

        Pipeline:
          1. Grayscale
          2. Upscale small images (helps with low-res photos of documents)
          3. Denoise
          4. CLAHE contrast enhancement
          5. Sharpening
          6. Otsu binarization → crisp black-on-white text

        Returns path to preprocessed temp file, or None on failure.
        """
        try:
            import cv2
            import numpy as np

            img = cv2.imread(image_path)
            if img is None:
                logger.warning(f"cv2 could not read {image_path}")
                return None

            # 1. Grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 2. Upscale if image is small (phone photos of documents can be fine,
            #    but thumbnails or small crops often need upscaling)
            h, w = gray.shape
            if max(h, w) < 1000:
                scale = 1000 / max(h, w)
                gray = cv2.resize(gray, None, fx=scale, fy=scale,
                                  interpolation=cv2.INTER_CUBIC)
                logger.debug(f"Upscaled image by {scale:.1f}x to improve OCR")

            # 3. Denoise — fast non-local means
            gray = cv2.fastNlMeansDenoising(gray, h=15, templateWindowSize=7,
                                            searchWindowSize=21)

            # 4. CLAHE — adaptive contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)

            # 5. Sharpening kernel
            kernel = np.array([[0, -1, 0],
                                [-1, 5, -1],
                                [0, -1, 0]])
            gray = cv2.filter2D(gray, -1, kernel)
            gray = np.clip(gray, 0, 255).astype(np.uint8)

            # 6. Otsu binarization — clean black text on white background
            _, binary = cv2.threshold(gray, 0, 255,
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Write to temp file
            fd, tmp_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            cv2.imwrite(tmp_path, binary)
            return tmp_path

        except ImportError:
            logger.warning("opencv-python not installed; skipping preprocessing")
            return None
        except Exception as e:
            logger.error(f"OCR preprocessing failed: {e}")
            return None

    def _merge_regions(
        self,
        regions_a: List[Dict],
        regions_b: List[Dict],
        spatial_threshold: int = 30,
    ) -> List[Dict]:
        """
        Merge two region lists. Keep the higher-confidence detection when two
        regions overlap (centre within spatial_threshold px of each other).
        """
        merged = list(regions_a)

        for rb in regions_b:
            bxs = [p[0] for p in rb["bbox"]]
            bys = [p[1] for p in rb["bbox"]]
            bcx = sum(bxs) / len(bxs)
            bcy = sum(bys) / len(bys)

            duplicate = False
            for i, ra in enumerate(merged):
                axs = [p[0] for p in ra["bbox"]]
                ays = [p[1] for p in ra["bbox"]]
                acx = sum(axs) / len(axs)
                acy = sum(ays) / len(ays)

                if abs(bcx - acx) < spatial_threshold and abs(bcy - acy) < spatial_threshold:
                    # Keep whichever has higher confidence
                    if rb["confidence"] > ra["confidence"]:
                        merged[i] = rb
                    duplicate = True
                    break

            if not duplicate:
                merged.append(rb)

        return merged

    def extract_text(self, image_path: str, min_confidence: float = 0.2) -> Dict:
        """
        Run OCR on an image file using a dual-pass strategy:
          Pass 1 — preprocessed (binarized) image: best for printed documents
          Pass 2 — original image: best for coloured/stylised text

        Results are merged; duplicates resolved by keeping higher confidence.

        Returns:
            {
                "full_text": "concatenated text",
                "regions": [...],
                "has_text": bool
            }
        """
        self._load_reader()

        preprocessed_path = None
        regions_preprocessed: List[Dict] = []
        regions_original: List[Dict] = []

        # ── Pass 1: preprocessed image ────────────────────────────────────────
        try:
            preprocessed_path = self._preprocess_for_ocr(image_path)
            if preprocessed_path:
                raw = self._reader.readtext(preprocessed_path)
                for bbox, text, confidence in raw:
                    text = text.strip()
                    if text and confidence >= min_confidence:
                        regions_preprocessed.append({
                            "text": text,
                            "confidence": round(float(confidence), 4),
                            "bbox": [[int(p[0]), int(p[1])] for p in bbox],
                        })
                logger.info(
                    f"OCR pass-1 (preprocessed): {len(regions_preprocessed)} regions"
                )
        except Exception as e:
            logger.error(f"OCR pass-1 failed: {e}")
        finally:
            if preprocessed_path and os.path.exists(preprocessed_path):
                try:
                    os.remove(preprocessed_path)
                except OSError:
                    pass

        # ── Pass 2: original image ─────────────────────────────────────────────
        try:
            raw = self._reader.readtext(image_path)
            for bbox, text, confidence in raw:
                text = text.strip()
                if text and confidence >= min_confidence:
                    regions_original.append({
                        "text": text,
                        "confidence": round(float(confidence), 4),
                        "bbox": [[int(p[0]), int(p[1])] for p in bbox],
                    })
            logger.info(
                f"OCR pass-2 (original): {len(regions_original)} regions"
            )
        except Exception as e:
            logger.error(f"OCR pass-2 failed: {e}")

        # ── Merge both passes ─────────────────────────────────────────────────
        # Start with preprocessed (usually better for documents), add non-
        # overlapping regions from original pass.
        if regions_preprocessed:
            all_regions = self._merge_regions(regions_preprocessed, regions_original)
        else:
            all_regions = regions_original

        # Sort top-to-bottom, left-to-right for natural reading order
        def region_sort_key(r):
            ys = [p[1] for p in r["bbox"]]
            xs = [p[0] for p in r["bbox"]]
            return (min(ys), min(xs))

        all_regions.sort(key=region_sort_key)

        full_text = " ".join(r["text"] for r in all_regions)

        logger.info(
            f"OCR final: {len(all_regions)} region(s): "
            f"{full_text[:120]}{'…' if len(full_text) > 120 else ''}"
        )

        return {
            "full_text": full_text,
            "regions": all_regions,
            "has_text": bool(all_regions),
        }


# Module-level singleton
ocr_extractor = OCRExtractor(languages=["en"])