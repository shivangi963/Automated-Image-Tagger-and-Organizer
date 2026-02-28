"""
YOLO object detector — handles the "hard" object detections
(person, car, dog, cat, bottle, phone…) that BLIP/CLIP are less precise about.

Combined with scene_tagger.py (BLIP + CLIP) this gives both:
  • Precise object boxes    — YOLO
  • Rich scene / context    — BLIP caption + CLIP zero-shot tags

Model: YOLOv8n (nano) by default — very fast, ~6 MB, runs on CPU.
Swap to "yolov8s.pt" or "yolov8m.pt" for better accuracy.
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Default confidence threshold — detections below this are discarded
CONFIDENCE_THRESHOLD = 0.30


class YOLODetector:
    """Lazy-loading YOLOv8 wrapper."""

    def __init__(self, model_name: str = "yolov8n.pt", confidence: float = CONFIDENCE_THRESHOLD):
        self._model = None
        self._model_name = model_name
        self._confidence = confidence

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLO model '{self._model_name}' (downloads ~6 MB on first run)…")
            self._model = YOLO(self._model_name)
            self._model.fuse()
            logger.info("✓ YOLO loaded")
        except Exception as e:
            logger.error(f"Failed to load YOLO: {e}")
            raise

    def detect_objects(self, image_path: str) -> List[Dict]:
        """
        Run YOLO detection on an image file.

        Returns a list of detection dicts:
            [{"label": "person", "confidence": 0.92, "bbox": [x1, y1, x2, y2]}, ...]
        """
        self._load_model()
        try:
            results = self._model.predict(
                source=image_path,
                conf=self._confidence,
                verbose=False,
            )
            detections = []
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    label = result.names[cls_id]
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = [round(float(v), 1) for v in box.xyxy[0]]
                    detections.append({
                        "label": label,
                        "confidence": round(conf, 4),
                        "bbox": [x1, y1, x2, y2],
                    })
            logger.info(f"YOLO detected {len(detections)} object(s) in {image_path}")
            return detections
        except Exception as e:
            logger.error(f"YOLO inference error: {e}")
            return []

    def extract_unique_labels(self, detections: List[Dict]) -> List[Dict]:
        """
        Collapse multiple boxes of the same class into one entry,
        keeping the highest-confidence instance.

        [{"label": "person", "confidence": 0.92}, ...]
        """
        best: Dict[str, float] = {}
        for d in detections:
            label = d["label"]
            conf = d["confidence"]
            if label not in best or conf > best[label]:
                best[label] = conf
        return [{"label": lbl, "confidence": conf} for lbl, conf in best.items()]


# Module-level singleton
detector = YOLODetector()