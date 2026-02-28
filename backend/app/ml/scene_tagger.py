"""
Scene Tagger: combines BLIP captioning + CLIP zero-shot classification
to produce rich semantic tags (sky, beach, indoor, outdoor, etc.)
that YOLO cannot detect.
"""
import re
import logging
from typing import List, Dict, Optional
from PIL import Image
import torch

logger = logging.getLogger(__name__)

# ── CLIP zero-shot tag vocabulary ────────────────────────────────────────────
# These are evaluated in batches against the image embedding.
# Add / remove freely — no retraining needed.
CLIP_TAGS = [
    # Sky & weather
    "blue sky", "cloudy sky", "sunset sky", "night sky", "foggy", "rainy", "snowy",
    # Water & coast
    "beach", "ocean", "sea", "lake", "river", "waterfall", "swimming pool",
    # Terrain
    "mountain", "forest", "jungle", "desert", "snow field", "countryside",
    "grassland", "rocks", "sand dunes", "volcano",
    # Urban / built
    "city skyline", "urban street", "suburb", "bridge", "highway",
    "construction site", "parking lot",
    # Indoor scenes
    "kitchen", "bedroom", "living room", "office", "restaurant",
    "gym", "library", "bathroom", "shopping mall", "hospital",
    "classroom", "warehouse",
    # Time / lighting
    "daytime", "nighttime", "sunrise", "sunset", "golden hour",
    "dark scene", "bright scene",
    # Nature extras
    "flowers", "garden", "trees", "autumn leaves", "farm", "vineyard",
    # Transport
    "airport", "train station", "harbor", "parking",
    # Sport / activity
    "stadium", "playground", "swimming", "hiking trail",
]

# Stopwords for caption keyword extraction
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "of", "to", "for", "with", "and", "or", "but",
    "not", "that", "this", "it", "its", "there", "their", "they", "them",
    "some", "has", "have", "had", "by", "from", "up", "as", "into",
    "through", "about", "over", "after", "which", "what", "when",
    "where", "who", "will", "can", "could", "would", "should",
}


class SceneTagger:
    """
    Lazy-loading wrapper around BLIP + CLIP.
    Models are downloaded on first use (~900 MB BLIP, ~600 MB CLIP).
    Both run on CPU by default; move to CUDA automatically if available.
    """

    def __init__(self):
        self._blip_processor = None
        self._blip_model = None
        self._clip_processor = None
        self._clip_model = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    # ── lazy loaders ──────────────────────────────────────────────────────────

    def _load_blip(self):
        if self._blip_model is not None:
            return
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration
            logger.info("Loading BLIP caption model (first run downloads ~900 MB)…")
            self._blip_processor = BlipProcessor.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            )
            self._blip_model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            ).to(self._device)
            self._blip_model.eval()
            logger.info("✓ BLIP loaded")
        except Exception as e:
            logger.error(f"Failed to load BLIP: {e}")
            raise

    def _load_clip(self):
        if self._clip_model is not None:
            return
        try:
            from transformers import CLIPProcessor, CLIPModel
            logger.info("Loading CLIP model (first run downloads ~600 MB)…")
            self._clip_processor = CLIPProcessor.from_pretrained(
                "openai/clip-vit-base-patch32"
            )
            self._clip_model = CLIPModel.from_pretrained(
                "openai/clip-vit-base-patch32"
            ).to(self._device)
            self._clip_model.eval()
            logger.info("✓ CLIP loaded")
        except Exception as e:
            logger.error(f"Failed to load CLIP: {e}")
            raise

    # ── public methods ────────────────────────────────────────────────────────

    def generate_caption(self, image: Image.Image) -> str:
        """Return a natural-language caption for the image."""
        self._load_blip()
        inputs = self._blip_processor(image, return_tensors="pt").to(self._device)
        with torch.no_grad():
            ids = self._blip_model.generate(**inputs, max_new_tokens=60)
        caption = self._blip_processor.decode(ids[0], skip_special_tokens=True)
        logger.debug(f"BLIP caption: {caption}")
        return caption

    def classify_scenes(
        self, image: Image.Image, top_k: int = 10, threshold: float = 0.015
    ) -> List[Dict]:
        """
        Zero-shot CLIP classification against CLIP_TAGS.
        Returns up to top_k tags whose softmax probability > threshold.
        """
        self._load_clip()

        # Process in batches to avoid OOM on large tag lists
        batch_size = 32
        all_probs = []

        for i in range(0, len(CLIP_TAGS), batch_size):
            batch = CLIP_TAGS[i : i + batch_size]
            inputs = self._clip_processor(
                text=batch,
                images=image,
                return_tensors="pt",
                padding=True,
                truncation=True,
            ).to(self._device)
            with torch.no_grad():
                logits = self._clip_model(**inputs).logits_per_image  # (1, batch)
                all_probs.extend(logits[0].tolist())

        # Softmax over ALL tags together for a fair comparison
        import torch.nn.functional as F
        probs = F.softmax(torch.tensor(all_probs), dim=0).tolist()

        results = [
            {"label": tag, "confidence": round(prob, 4)}
            for tag, prob in zip(CLIP_TAGS, probs)
            if prob > threshold
        ]
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[:top_k]

    def caption_to_tags(self, caption: str) -> List[str]:
        """Extract meaningful single-word tokens from a caption."""
        words = re.findall(r"\b[a-zA-Z]+\b", caption.lower())
        return [w for w in words if w not in _STOPWORDS and len(w) > 2]

    def tag_image(self, image: Image.Image) -> Dict:
        """
        Main entry point.
        Returns:
            {
                "caption": str,
                "caption_tags": [str, ...],
                "scene_tags": [{"label": str, "confidence": float}, ...]
            }
        """
        result = {"caption": "", "caption_tags": [], "scene_tags": []}

        try:
            caption = self.generate_caption(image)
            result["caption"] = caption
            result["caption_tags"] = self.caption_to_tags(caption)
        except Exception as e:
            logger.error(f"BLIP captioning error: {e}")

        try:
            result["scene_tags"] = self.classify_scenes(image)
        except Exception as e:
            logger.error(f"CLIP scene classification error: {e}")

        return result


# Module-level singleton — imported by celery worker
scene_tagger = SceneTagger()