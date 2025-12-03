from ultralytics import YOLO
from app.config import settings
import logging
from typing import List, Dict
import numpy as np

logger = logging.getLogger(__name__)


class YOLODetector:
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model"""
        try:
            logger.info(f"Loading YOLO model: {settings.YOLO_MODEL}")
            self.model = YOLO(settings.YOLO_MODEL)
            logger.info("YOLO model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading YOLO model: {e}")
            raise
    
    def detect_objects(self, image_path: str) -> List[Dict]:
        """
        Detect objects in image
        Returns list of detections with label, confidence, and bbox
        """
        if not self.model:
            raise RuntimeError("YOLO model not loaded")
        
        try:
            # Run inference
            results = self.model.predict(
                image_path,
                conf=settings.YOLO_CONFIDENCE,
                verbose=False
            )
            
            detections = []
            
            # Process results
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # Get class name and confidence
                    cls_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    label = result.names[cls_id]
                    
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    detection = {
                        'label': label,
                        'confidence': round(confidence, 3),
                        'bbox': {
                            'x1': round(x1, 2),
                            'y1': round(y1, 2),
                            'x2': round(x2, 2),
                            'y2': round(y2, 2)
                        }
                    }
                    
                    detections.append(detection)
            
            logger.info(f"Detected {len(detections)} objects")
            return detections
            
        except Exception as e:
            logger.error(f"Error during detection: {e}")
            return []
    
    def extract_unique_labels(self, detections: List[Dict]) -> List[Dict]:
        """
        Extract unique labels with highest confidence
        Returns list of {label, confidence}
        """
        label_confidence = {}
        
        for detection in detections:
            label = detection['label']
            confidence = detection['confidence']
            
            if label not in label_confidence or confidence > label_confidence[label]:
                label_confidence[label] = confidence
        
        # Convert to list and sort by confidence
        unique_labels = [
            {'label': label, 'confidence': conf}
            for label, conf in label_confidence.items()
        ]
        
        unique_labels.sort(key=lambda x: x['confidence'], reverse=True)
        
        return unique_labels


# Global detector instance
detector = YOLODetector()