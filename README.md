# DeepTrace AI

Explainable digital-image forensics. Upload an image and get metadata/EXIF findings, Error Level Analysis (ELA),
noise and image statistics, content-credential detection, an optional AI-generation detector score, a cautious
combined assessment, persistent history, and a downloadable PDF report.

> **DeepTrace AI is an investigative aid, not proof.** It never declares an image "fake" or "authentic" and
> never outputs a probability of authenticity. Absence of indicators does not mean an image is genuine.

## What is implemented (and its status)

| Capability | Status |
|---|---|
| Upload validation by real content (size, pixel limits, corrupt/empty/non-image rejected) | Implemented, verified by running the service directly |
| EXIF/metadata findings (GPS values and personal fields redacted by default) | Implemented, verified |
| ELA map + statistics (visual aid; never auto-scored) | Implemented, verified |
| Noise / sharpness / histogram / JPEG-quantization measurements | Implemented, verified |
| C2PA content-credential **detection** | Detection only; signatures are **not** verified |
| AI-generation detector (ONNX, CPU) | Runs and returns a raw uncalibrated score; **accuracy not benchmarked**. Reports `unavailable` if disabled, or if the runtime/model is missing |
| Combined assessment (4 cautious categories) | Implemented; transparent rules, not a calibrated model |
| SQLite history, open, delete, 30-day retention | Implemented |
| PDF report (ReportLab) | Implemented, verified to produce a valid PDF |
| React dashboard: analyzer, results, history (open/PDF/delete), methodology & privacy | Implemented; ESLint and syntax checks pass. Run `npm run build` and click through it on your machine before demoing |

## Architecture

```
frontend/   React 19 + Vite. src/api.js is the only place that talks to the backend.
backend/    FastAPI. app/analysis/* (checks) -> app/services/analysis_service.py -> SQLite + files in storage/
```

## Run it (Windows PowerShell)

Backend (Python 3.11+):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env        # optional; set DEEPTRACE_AI_DETECTOR=onnx to enable the detector
uvicorn app.main:app --reload       # http://127.0.0.1:8000/docs
```

Frontend (Node 20+):

```powershell
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

The frontend calls `http://127.0.0.1:8000` by default. To change it, copy `frontend/.env.example` to
`frontend/.env.local` and set `VITE_API_BASE_URL`; add the frontend's origin to `DEEPTRACE_CORS_ORIGINS` in
`backend/.env`. Check `GET /api/v1/health` to see whether the AI detector is `available` or `unavailable`.

## Use it

1. Open the app, drop a JPEG/PNG/WebP (max 10 MB) into **Image Analyzer**, press **Analyze image**.
2. Read the overall assessment, then each evidence card; expand "Limitations" and finding details.
3. **Download PDF report**. Past analyses are listed under **History** (view / PDF / delete).

## Tests and build

```powershell
cd backend;  pytest -v
cd frontend; npm run lint; npm run build
```

## Privacy and data handling

Uploads are analysed in memory and not written to disk. Stored per analysis: result JSON, a downscaled
preview, the ELA image and the PDF, under `backend/storage/`. Delete from the History panel, or rely on the
retention cleanup (default 30 days, applied at backend start). There is no authentication or rate limiting;
run on a trusted machine/network.

## Known limitations

- ELA, statistics and metadata are heuristics with false positives and false negatives. Screenshots,
  messaging-app re-compression and edits that re-save the whole image weaken all of them.
- The AI detector is one pretrained model of unmeasured accuracy; do not rely on it alone.
- No C2PA signature verification; use `c2patool` or the Content Credentials verifier for that.
- Animated images: only the first frame is analysed. Upload size is enforced after receipt.
- `frontend/dist`, `.venv` and `node_modules` in the original archive are Windows build artifacts and are not
  portable; rebuild them on your machine.
