# DeepTrace AI - Backend

Explainable digital image forensics API. Upload a suspicious image and get metadata findings,
Error Level Analysis (ELA), image statistics, AI-detector status, content-credential detection,
an evidence-based assessment and a PDF report.

> DeepTrace AI is an **investigative aid, not an infallible authenticity verifier.** It never
> reports an image as definitely fake or authentic, and it gives no fake-probability number.

## What is real, and what is not

| Capability | Status in this build |
|---|---|
| Upload validation (real content check, size/pixel limits) | Implemented |
| Metadata / EXIF inspection with findings | Implemented |
| ELA with evidence image (visual aid, no automatic threshold) | Implemented |
| Image statistics (channels, entropy, sharpness, noise, JPEG quantization) | Implemented |
| Explainable assessment (4 cautious categories) | Implemented |
| PDF report (ReportLab), SQLite history, delete, retention cleanup | Implemented |
| **AI-generated image detection** | **Optional, off unless configured.** `DEEPTRACE_AI_DETECTOR=onnx` runs the bundled `models/model_int8.onnx` through ONNX Runtime and returns a raw, **uncalibrated** model score. If `onnxruntime` or the model file is missing, or the setting is `none`, the API reports `unavailable` and never invents a score. Its accuracy has **not** been benchmarked by this project. |
| **C2PA verification** | **Detection only.** Embedded credentials are detected by file structure but signatures are **not verified** (`verification: "not_performed"`) |

## Architecture

```
backend/
  app/
    main.py            create_app(): wiring, CORS, startup (DB init, retention cleanup)
    config.py          settings from DEEPTRACE_* environment variables / .env
    schemas.py         Pydantic response models
    database.py        SQLite repository (stdlib, parameterized SQL, corrupt-DB recovery)
    api/routes.py      HTTP endpoints (thin)
    services/analysis_service.py   orchestrates one analysis; isolates failures per module
    analysis/          validation, metadata, ela, image_statistics, ai_detection,
                       provenance, assessment, report (PDF), common
    utils/file_utils.py  ID validation, filename sanitising, safe path joining
  tests/               pytest suite
  storage/             uploads/ (unused: uploads are not saved), evidence/, reports/, deeptrace.db
```

Each check runs in isolation: if one fails, the others still report and the result status becomes `partial`.

## Requirements

Python 3.11+ (the non-HTTP test suite was run on Python 3.12; verify on your 3.11.9 with `pytest`). Windows PowerShell commands below.

## Setup (PowerShell)

```powershell
cd $HOME\Documents\deeptrace-ai\backend      # adjust to your folder
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt            # includes onnxruntime for the optional AI detector
Copy-Item .env.example .env                  # optional
```

If activation is blocked: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

## Run

```powershell
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs (Swagger UI). OpenAPI schema: http://127.0.0.1:8000/openapi.json

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | App name, version, status |
| GET | `/health` | Simple health check |
| GET | `/api/v1/health` | Versioned health with database/storage/detector status |
| POST | `/api/v1/analyze` | Upload image (multipart field `file`) and analyse |
| GET | `/api/v1/analyses?limit=20&offset=0` | History, newest first |
| GET | `/api/v1/analyses/{id}` | Stored result |
| GET | `/api/v1/analyses/{id}/report` | Download PDF |
| GET | `/api/v1/analyses/{id}/evidence/{name}` | Evidence image (`ela.png`, `preview.jpg`) |
| DELETE | `/api/v1/analyses/{id}` | Delete analysis and its files |

Errors are JSON: `{"detail": "..."}`. Codes: 400 empty, 413 too large, 415 not an image / unsupported
format, 422 corrupted or malformed request, 404 unknown id.

### Example upload

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/analyze" -F "file=@C:\path\to\photo.jpg"
curl.exe -o report.pdf "http://127.0.0.1:8000/api/v1/analyses/<analysis_id>/report"
```
In Swagger: `POST /api/v1/analyze` -> *Try it out* -> choose file -> *Execute*.

### Assessment categories

`no_strong_indicators_found`, `inconclusive`, `potential_manipulation_indicators`, `analysis_incomplete`.
Derived only from findings of strength `weak` / `moderate` (one weak = inconclusive; one moderate or
two weak = potential indicators). ELA output is **never** scored automatically. These rules are
transparent heuristics, not a calibrated model.

## Tests

```powershell
pytest -v
```
Tests use generated images and temporary storage; no network, paid service or model download.

## Storage and retention

- The **uploaded file is processed in memory and never written to disk.** `storage/uploads/` is reserved and unused.
- Kept per analysis: result JSON and safe image summary (SQLite), `ela.png`, a downscaled `preview.jpg`
  (set `DEEPTRACE_STORE_PREVIEW=false` to disable), and the PDF report (which embeds both images).
- The sanitised original filename and SHA-256 are stored. EXIF is stored in the result JSON with personal
  fields (artist, owner, serial numbers) redacted and GPS coordinates withheld by default.
- Analyses older than `DEEPTRACE_RETENTION_DAYS` (default 30) are deleted at startup. `DELETE` removes
  the row, evidence folder and report of that analysis only.
- Internal IDs are random 32-hex strings; paths are never built from user input and never returned.

## Known limitations

- The AI detector is a single pretrained model with unmeasured accuracy here; treat its score as a weak signal. There is no C2PA signature verification (see table above).
- ELA, statistics and metadata are heuristics with known false positives and false negatives.
- Animated images: only the first frame is analysed.
- Upload size is enforced after the multipart body is received (set limits at your reverse proxy for production).
- No authentication or rate limiting (hackathon scope).

## Troubleshooting (Windows)

- `uvicorn` not recognized: activate the venv first.
- `No module named 'app'`: run commands from the `backend` folder.
- Port busy: `uvicorn app.main:app --reload --port 8001`.
- `pip install` fails for opencv/numpy: use Python 3.11 or 3.12 (64-bit) and upgrade pip.
- CORS error from a frontend: add its origin to `DEEPTRACE_CORS_ORIGINS` and restart.
- Database errors: stop the server and delete `storage\deeptrace.db` (a corrupt file is also set aside automatically).
