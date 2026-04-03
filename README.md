# Striplens — Backend

Backend API for **Striplens**, a mobile application that analyzes Lateral Flow Test (LFT) strips by detecting and quantifying the intensity of test and control lines to determine positive/negative results.

## Overview

The backend receives an image of an LFT strip, runs it through a multi-stage image processing pipeline, and returns intensity values for the control and test lines along with S3-hosted URLs for all intermediate images.

## Tech Stack

- **Framework:** FastAPI (Python)
- **Image Processing:** CarveKit (background removal), OpenCV, Pillow, SciPy
- **Cloud Storage:** AWS S3 (boto3)
- **Server:** Uvicorn

## Processing Pipeline

1. **Background Removal** — CarveKit (TracerUniversalB7 + FBAMatting) isolates the LFT strip from the background.
2. **Straighten & Orient** — Detects the strip's rotation via contour analysis on the alpha channel; corrects orientation using the red arrow marker on the strip.
3. **Crop** — Crops to the region of interest containing the test and control lines; applies contrast enhancement.
4. **Intensity Analysis** — Converts to grayscale, applies Gaussian smoothing, and uses `scipy.signal.find_peaks` to locate peaks corresponding to the control and test lines. Peak areas are integrated via `scipy.integrate.trapezoid`.
5. **Storage** — All intermediate images (original, background-removed, processed, cropped, intensity plot) are uploaded to AWS S3.

The API returns `controlLine` and `testLine` float intensity values plus S3 URLs for each image.

## Setup

### Prerequisites

- Python 3.12+
- AWS account with an S3 bucket (`striplensapp` by default)

### Install dependencies

```bash
pip install -r app/requirements.txt
```

### Configure environment

Create `app/.env`:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=your_region
S3_BUCKET=striplensapp
TEMP_DIR=/tmp/striplens
DEV_MODE=True
DEBUG=False
```

Set `DEV_MODE=True` during local development — this skips S3 bucket validation on startup, allowing the server to run without live AWS credentials.

### Run the server

```bash
cd app && python main.py
```

The server starts on `http://0.0.0.0:8000`. To allow the Striplens mobile app to connect from a device on the same network, ensure the server is accessible at `<your-machine-ip>:8000` and update the frontend's `HandleProcess.tsx` with that address.

### Docker

```bash
docker build -t striplens-backend .
docker run -p 8000:8000 --env-file app/.env striplens-backend
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check; returns version and AWS config status |
| POST | `/image/process` | Full processing pipeline — accepts a multipart image upload, returns intensity values and S3 URLs |
| POST | `/image/test/upload` | Validates and uploads a file to S3 (testing) |
| POST | `/image/upload-test` | Raw S3 upload without validation (testing) |

### Process endpoint

**Request:** `POST /image/process`  
Content-Type: `multipart/form-data`  
Field: `file` — JPEG, PNG, or WebP image (max 10 MB)

**Response:**
```json
{
  "Status": "200 OK",
  "message": "Image processed successfully",
  "bucket_name": "striplensapp",
  "folder_name": "strip_image/",
  "urls": {
    "Original": "https://...",
    "removedbg": "https://...",
    "processed": "https://...",
    "cropped": "https://...",
    "plot": "https://..."
  },
  "intensity": {
    "controlLine": 4.32,
    "testLine": 1.87
  }
}
```

## Project Structure

```
app/
├── main.py                      # App factory, middleware, exception handlers
├── core/
│   ├── config.py                # Settings (pydantic-settings, reads app/.env)
│   └── exceptions.py            # Custom exception hierarchy
├── api/endpoints/
│   ├── health.py
│   └── image.py                 # Upload and process endpoints
├── services/
│   ├── image_processor.py       # Orchestrates the full pipeline
│   ├── image_utils.py           # CV logic: straighten, crop, peak detection
│   ├── removebg.py              # CarveKit background removal
│   └── s3.py                    # AWS S3 operations
└── schemas/
    └── image.py                 # Pydantic response models
```

## Related

- **Frontend:** React Native app built with Expo. Connects to this backend via the `/image/process` endpoint.
- **Storage:** All processed images are stored in AWS S3 and returned as pre-signed public URLs for display in the mobile app.
