# Smart Gallery — Automated Image Tagger & Organizer

An AI-powered image management platform that automatically tags, captions, and organizes your photos using YOLO, BLIP, CLIP, and EasyOCR.

---

##  Features

- **AI Auto-Tagging** — YOLO detects objects (person, car, dog…); CLIP classifies scenes (beach, sunset, indoors…)
- **Natural Language Captions** — BLIP generates human-readable descriptions for every image
- **OCR Text Extraction** — EasyOCR reads text embedded in images (signs, labels, screenshots)
- **Duplicate Detection** — Perceptual hashing (pHash) finds near-duplicate images with configurable similarity threshold
- **Smart Search** — Full-text search across all AI-generated tags and extracted text
- **Albums** — Create and manage curated collections
- **Async Processing** — Celery + Redis pipeline handles AI inference in the background so uploads feel instant
- **Presigned Uploads** — Files go directly from browser to MinIO (no proxy through FastAPI)


---

## Tech Stack

| Layer | Technology |
| Frontend | React 19, Vite 7, MUI v7, TanStack Query, Axios |
| Backend | FastAPI, Python 3.11+, Pydantic v2 |
| Task Queue | Celery 5, Redis 7 |
| Database | MongoDB 7 (async via Motor) |
| Object Storage | MinIO |
| ML: Detection | YOLOv8 (Ultralytics) |
| ML: Captioning | BLIP (`Salesforce/blip-image-captioning-base`) |
| ML: Scenes | CLIP (`openai/clip-vit-base-patch32`) |
| ML: OCR | EasyOCR |
| Auth | JWT (python-jose) + Argon2 password hashing |

---

##  Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### 1. Clone & configure

```bash
git clone <repo-url>
cd <project-dir>
cp .env.example .env   # edit secrets if needed (defaults work for local dev)
```

### 2. Start infrastructure

```bash
docker compose up -d
```

This starts MongoDB (27018), MinIO (9000 / 9001), and Redis (6379).

Verify services are healthy:

```bash
docker compose ps
```

### 3. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r ../requirements.txt
```

Start the FastAPI server:

```bash
uvicorn app.main:app --reload --port 8000
```

Start the Celery worker (new terminal, same venv):

```bash
celery -A celery_worker worker --loglevel=info --concurrency=2
```

> **First run note:** YOLO (~6 MB), BLIP (~900 MB), CLIP (~600 MB), and EasyOCR (~200 MB) models download automatically when the first image is processed. This is a one-time download.

### 4. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).


---

##  Environment Variables

Create a `.env` file in the project root. All values below are the defaults for local development.

```env
# MongoDB
MONGODB_URL=mongodb://admin:admin123@localhost:27018/?authSource=admin
MONGODB_DB=image_tagger

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=images
MINIO_SECURE=false

# Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# JWT
SECRET_KEY=change-me-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# YOLO
YOLO_MODEL=yolov8n.pt
YOLO_CONFIDENCE=0.25

# Upload limits
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,bmp,webp

# CORS
CORS_ORIGINS=http://localhost:5173
```

---

##  API Reference

Base URL: `http://localhost:8000`

All endpoints except `/auth/register` and `/auth/login` require:
```
Authorization: Bearer <jwt>
```

### Auth

| Method | Path | Description |
| POST | `/auth/register` | Create account, returns JWT |
| POST | `/auth/login` | Login, returns JWT |
| GET | `/auth/me` | Current user info |

### Images

| Method | Path | Description |
| GET | `/images/` | List all images (with embedded URLs) |
| GET | `/images/{id}` | Single image detail |
| POST | `/images/presign` | Get presigned PUT URL for direct MinIO upload |
| POST | `/images/ingest` | Register uploaded object and queue AI processing |
| POST | `/images/upload` | Multipart upload (alternative to presign+ingest) |
| DELETE | `/images/{id}` | Delete image from storage and DB |

### Search

| Method | Path | Query Params | Description |
| GET | `/search/` | `query`, `tags`, `date_from`, `date_to`, `skip`, `limit` | Full-text + tag search |
| GET | `/search/duplicates` | `threshold` (default 10) | Find duplicate groups |

### Albums

| Method |  Path |            Description |
| GET |   `/albums/` |       List user albums |
| POST |  `/albums/` |       Create album |
| GET |   `/albums/{id}` |   Album detail |
| PUT |   `/albums/{id}` |   Update album name/description |
| DELETE |`/albums/{id}` |    Delete album |
| GET |   `/albums/{id}/images` | Images in album |
| POST |  `/albums/{id}/images` | Add images to album |
| DELETE |`/albums/{id}/images/{image_id}` | Remove image from album |



##  AI Pipeline

When an image is uploaded, a Celery task runs the following pipeline:

```
Download from MinIO
    
Extract metadata (width, height, format, EXIF)
    
Generate thumbnail (400×400, JPEG 85%)
    
Compute pHash (perceptual hash for duplicate detection)
    
YOLO object detection  → ["person", "car", "dog", ...]
    
BLIP image captioning  → "a dog running on a beach"
BLIP keyword extraction → ["dog", "running", "beach"]
    
CLIP zero-shot scenes  → ["beach", "daytime", "blue sky"]
    
EasyOCR text extraction → ["STOP", "Main St"]
    
Merge all tags + deduplicate
    
Save to MongoDB (tags, caption, ocr_text, thumbnail_key, status: completed)
```

**Tag sources stored per tag:**
- `yolo` — object detection boxes
- `blip_caption` — keywords extracted from the BLIP description
- `clip_scene` — zero-shot scene labels
- `ocr` — individual words found by EasyOCR

---

##  Development Tips

### Check Celery task status

```bash
# Watch worker logs
celery -A celery_worker worker --loglevel=debug

# Monitor with Flower (optional)
pip install flower
celery -A celery_worker flower --port=5555
# Open http://localhost:5555
```

### Access MinIO console

Open [http://localhost:9001](http://localhost:9001) — login with `minioadmin` / `minioadmin123`.

### Reset the database

```bash
docker compose down -v   # removes named volumes (all data)
docker compose up -d
``

### Run with a better YOLO model

Edit `.env`:
```env
YOLO_MODEL=yolov8s.pt    # small — better accuracy, ~22 MB
# or
YOLO_MODEL=yolov8m.pt    # medium — best CPU accuracy, ~52 MB
```

### GPU acceleration

If you have CUDA, torch will automatically use the GPU for BLIP and CLIP (see `SceneTagger._device`). For YOLO, set `device=0` in `detect_objects()`.

---

##  Production Checklist

- [ ] Change `SECRET_KEY` to a long random string
- [ ] Set `MINIO_SECURE=true` and use HTTPS endpoints
- [ ] Use strong MongoDB credentials
- [ ] Set `CORS_ORIGINS` to your actual frontend domain
- [ ] Use a production WSGI server: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
- [ ] Run Celery workers behind a process manager (systemd, supervisord)
- [ ] Add rate limiting to auth endpoints
- [ ] Store JWT secret in a secrets manager, not in `.env`

---

## Requirements Summary

Python packages of note (see `requirements.txt` for pinned versions):

- `fastapi`, `uvicorn` — async web framework
- `motor`, `pymongo` — async/sync MongoDB drivers
- `minio` — object storage client
- `celery`, `redis` — distributed task queue
- `ultralytics` — YOLOv8
- `transformers` — BLIP + CLIP (Hugging Face)
- `easyocr` — OCR
- `imagehash`, `pillow` — image utilities
- `python-jose`, `passlib`, `argon2-cffi` — auth

---

