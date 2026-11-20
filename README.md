# PhysioFlex

**AI- & IoT-assisted Digital Physiotherapy and Rehabilitation Platform**

PhysioFlex provides three independent role-specific portals (Doctor, Physiotherapist, Patient) connected through a shared backend. It supports:

- Camera-based pose estimation (MediaPipe) for joint angles, repetition counting and movement quality
- IoT-ready architecture (ESP32 + MPU6050 data can be posted to `/api/sessions`)
- Longitudinal progress tracking (ROM, pain, adherence)
- Clinical notes, assessments and alerts
- Decision-support information only (no autonomous diagnosis)

## Quick Start (Local)

```bash
cd physioflex_app
pip install -r requirements.txt
# or: pip install fastapi uvicorn python-multipart python-jose passlib bcrypt pydantic python-dotenv websockets aiofiles jinja2
export PATH=$PATH:/root/.local/bin   # if needed
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000**

### Demo Accounts (password for all: `password123`)

| Role              | Email                     |
|-------------------|---------------------------|
| Doctor            | doctor@physioflex.com     |
| Physiotherapist   | physio@physioflex.com     |
| Patient           | patient@physioflex.com    |

## Features Implemented

### Doctor Portal (`/doctor`)
- Assigned patients overview
- Clinical metrics (pain, ROM, adherence)
- Abnormal movement alerts
- Exercise session history
- Clinical notes

### Physiotherapist Portal (`/physio`)
- Patient assessment entry
- View / create rehabilitation plans
- Monitor exercise sessions (camera + IoT source)
- Progress and notes

### Patient Portal (`/patient`)
- Today's plan with one-click start
- Personal progress charts
- Session history

### Live Exercise (`/patient/exercise`)
- Real-time webcam + MediaPipe Pose
- Live knee angle, repetition counter, quality feedback
- Pain slider + complete session → saved to backend

## Architecture

```
Patient (Camera / IoT)
        ↓
   PhysioFlex API (FastAPI)
        ↓
   JSON Database (data/db.json)
        ↓
  Doctor  ·  Physiotherapist
```

- Auth: JWT (Bearer token)
- Storage: file-based JSON (easy to replace with MongoDB Atlas)
- Real-time: WebSocket endpoint `/ws/session/{patient_id}` ready for live dashboards
- Frontend: server-rendered Jinja2 + Tailwind CDN + vanilla JS

## Deploy (Free Options)

### Render / Railway / Fly.io

1. Push this folder to a GitHub repo
2. Create a new Web Service
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variable if desired: `SECRET_KEY=your-long-random-string`

### Docker (optional)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## IoT Integration (ESP32 + MPU6050)

Post sensor-derived sessions to the same endpoint:

```http
POST /api/sessions
Authorization: Bearer <patient-or-physio-token>
Content-Type: application/json

{
  "plan_id": "plan001",
  "exercise_id": "ex001",
  "exercise_name": "Seated Knee Extension",
  "reps_completed": 10,
  "target_reps": 12,
  "sets_completed": 3,
  "max_rom": 118,
  "avg_rom": 112,
  "quality": "Good",
  "pain_score": 3,
  "duration_seconds": 240,
  "source": "iot"
}
```

## Accuracy Notes

This demo uses MediaPipe Pose for joint-angle estimation. Report accuracy carefully:

- Measure ROM error against a goniometer on a test set
- Measure repetition counting error (e.g. ground-truth 20 → system 19)
- Do **not** claim overall “98% accuracy” without a proper evaluation dataset

## Project Structure

```
physioflex_app/
├── main.py              # FastAPI app + all routes
├── auth.py              # JWT helpers
├── database.py          # JSON DB + seed data
├── requirements.txt
├── data/db.json         # Auto-created on first run
├── static/js/api.js     # Frontend API client
└── templates/           # HTML portals
    ├── index.html
    ├── login.html
    ├── doctor.html
    ├── physio.html
    ├── patient.html
    └── exercise.html
```

## License

Educational / demonstration project. Clinical decisions remain the responsibility of qualified healthcare professionals.


## PWA + cross-device video prototype (updated)

This project now includes an installable PWA shell:
- `static/manifest.webmanifest`
- `static/sw.js`
- `static/icons/`
- `/service-worker.js` route in `main.py`

### Deploy for phone + laptop

Use the included Render Blueprint (`render.yaml`) for this FastAPI project. Push the repository to GitHub, create a Blueprint on Render, and set `MONGODB_URI` to the existing MongoDB Atlas connection string. Do not commit `.env`. After deployment, use the public HTTPS URL on every device; `127.0.0.1`/`localhost` on a phone refers to the phone itself.

### Install

- Android: open the public HTTPS URL in Chrome, then browser menu → Install app / Add to Home screen.
- iPhone: open the public HTTPS URL in Safari → Share → Add to Home Screen.
- Laptop: use the browser's install icon if available, or bookmark the HTTPS URL.

The service worker caches the app shell assets only. Secure patient data and API responses are not cached offline.

### Video calls

The prototype uses Jitsi Meet's external embed API for audio/video and the PhysioFlex WebSocket signaling endpoint for incoming-call prompts. Both participants must be online, signed in, and have the relevant portal open for in-app incoming-call prompts. Camera/microphone access requires HTTPS (or localhost during development). Test with two separate accounts and two devices. Public Jitsi rooms are not suitable for real clinical consultations without a privacy/security review.

### Verification status

Python syntax and inline JavaScript syntax were checked after these edits. A live deployment, MongoDB connection, camera permissions, and two-device call could not be verified from this workspace; test them after deployment.


## Troubleshooting alert failures

If the patient alert request returns HTTP 500, open Render → your service → Logs and find `Failed to create patient alert`. The traceback identifies whether the problem is MongoDB credentials/network access, database permissions, or another runtime error. Do not clear or reseed the existing Atlas database. This build accepts either `MONGO_DB_NAME` or `MONGODB_DB_NAME`; `MONGO_DB_NAME` takes precedence.

YouTube exercise IDs may be deleted, private, or have embedding disabled. Use the visible “search for this exercise on YouTube” fallback when a saved embed does not play.


## Agentic AI workflow (new)

PhysioFlex includes a bounded, tool-using agent coordinator in `/api/chat/message`:

1. **Coordinator** routes a request to a specialist: Safety & Symptom Monitor, Movement & Exercise Coach, Recovery Progress Analyst, Clinical Report Assistant, or Care Plan Coordinator.
2. **Specialist tools** retrieve only allow-listed patient information: recovery summary, recent sessions, active rehabilitation plans, and open alerts.
3. **Synthesis** uses the configured Gemini model with the retrieved tool results. The chat UI displays the selected agent and tools executed.
4. **Human approval boundary**: the AI cannot autonomously change a rehabilitation plan, diagnose a condition, or publish a clinical report. A clinician must make those changes through the portal and review the content.

This is an auditable, bounded agentic workflow—not an autonomous clinical decision-maker. Do not expose unrestricted database or arbitrary code-execution tools to the model.

## Exercise session tracking

The camera session now calculates a 2D knee flexion estimate from visible MediaPipe hip-knee-ankle landmarks. It tracks the observed flexion excursion during the session and counts a repetition only after a flexion-and-return cycle. Basic trunk/shoulder/hip alignment checks provide visual/audio cues.

**Measurement limitations:** single-camera 2D pose estimates are affected by camera angle, occlusion, lighting, body orientation, and landmark confidence. They are not clinically validated goniometer measurements. The current live session page is configured for knee flexion/extension; it does not yet provide exercise-specific biomechanics for every exercise in the catalogue. Do not use its output to change treatment without clinician assessment.

## Updating prescribed exercises

Physiotherapists can select a patient, open an existing plan, and edit the exercise selection, sets, repetitions, target ROM, frequency, and plan dates. Saving updates the existing plan rather than creating a duplicate.

## Clinical reports

Doctors can publish a clinical evaluation report from the selected patient's Doctor Portal panel. The patient can view published reports and download a server-generated PDF. Report access is checked against the authenticated user's patient access. PDF export requires `reportlab` (included in `requirements.txt`).

Reports are summaries of clinician-entered information; the application does not issue a regulated digital signature or certify the report as a hospital record.

## Secrets and database safety

- The example environment file contains placeholders only. Copy it to `.env` and supply your own credentials.
- Never commit `.env`, MongoDB connection strings, Gemini API keys, or production signing secrets.
- The uploaded archive contained live-looking credentials in its example environment file. **Rotate the MongoDB database password and Gemini API key before deploying this revised project.** Removing them from this copy does not revoke credentials already exposed.
- The example database name is `physioflex_v3` to avoid accidentally reusing the original project's database. Confirm the database name before connecting or running migrations.

Patient-specific agent tools and external LLM synthesis are gated by the patient's `automated_decision_support` consent setting. Without that consent, the system does not send patient-specific context to Gemini.
