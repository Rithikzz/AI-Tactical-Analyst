# Input Service

FastAPI-based input system for uploads, YouTube ingestion, live stream ingestion, and job tracking.

## Run
```bash
cd input_service
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints
- `POST /auth/login` login and receive JWT
- `POST /uploads` create upload session
- `POST /uploads/{upload_id}/parts?part_number=N` upload a part
- `POST /uploads/{upload_id}/complete` finalize upload and enqueue job
- `POST /ingest/youtube` enqueue YouTube job
- `POST /ingest/live` enqueue live stream job
- `GET /jobs/{job_id}` get job status
- `GET /jobs/{job_id}/analytics` download analytics JSON
- `GET /jobs/{job_id}/output` download output video
- `GET /uploads/{upload_id}` get upload status
- `WS /ws/jobs/{job_id}` realtime updates

## Outputs
- Final uploads: `input_service/var/uploads/`
- Processed outputs: `input_service/var/outputs/{job_id}/`
- Analytics JSON: `input_service/var/analytics/{job_id}.json`

## Notes
- Upload jobs run the full football analysis pipeline using `football_analysis/models/best.pt`.
- YouTube ingestion uses `yt-dlp` to download a video before processing.
- Live ingestion uses `ffmpeg` to capture `LIVE_CAPTURE_SECONDS` into a local MP4 before processing.

## Auth
Default admin:
- Email: `admin@local`
- Password: `admin123`

Override with environment variables:
`ADMIN_EMAIL`, `ADMIN_PASSWORD`, `JWT_SECRET`

Rate limiting:
`RATE_LIMIT_REQUESTS` per `RATE_LIMIT_WINDOW_SECONDS`
