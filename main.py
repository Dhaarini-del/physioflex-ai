"""
PhysioFlex – AI & IoT Assisted Digital Physiotherapy Platform
Full CRUD + real-time portal updates + dataset exercises
"""
from fastapi import FastAPI, Request, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import asyncio
import json
import os
from urllib.request import Request as URLRequest, urlopen
from urllib.error import URLError, HTTPError
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from database import get_db, save_db, generate_id, seed_if_empty, _now, append_event, log_audit_event, persist_patient_alert, update_user_language
from auth import (
    verify_password, create_access_token, get_current_user, get_password_hash,
    require_role, TokenData, UserOut,
)
from ml_routes import ml_router
from ml_service import ml_service

PENDING_ACCOUNT_MSG = (
    "Your account is waiting for administrator approval. "
    "You can view exercises and health tips until then."
)
REJECTED_ACCOUNT_MSG = (
    "Your registration was declined. Please contact the clinic administrator."
)

HEALTH_TIPS = [
    {
        "id": "ht1",
        "title": "Warm up before any movement practice",
        "category": "Safety",
        "body": "Spend 5–8 minutes on gentle joint circles and easy walking before stretching or strengthening. Cold tissue is more likely to feel stiff or painful.",
    },
    {
        "id": "ht2",
        "title": "Pain is a signal, not a target",
        "category": "Pain",
        "body": "Mild muscle effort is expected. Sharp, shooting, or worsening pain is a stop sign. Rest, ice if swollen, and wait for your clinician after you are approved.",
    },
    {
        "id": "ht3",
        "title": "Breathe through each repetition",
        "category": "Technique",
        "body": "Exhale on effort and avoid holding your breath. Steady breathing helps you control the movement and reduces unnecessary tension.",
    },
    {
        "id": "ht4",
        "title": "Quality over extra repetitions",
        "category": "Technique",
        "body": "A smaller, controlled range is safer than forcing a larger one. Keep both sides of the body as even as you can and stop if you start compensating.",
    },
    {
        "id": "ht5",
        "title": "Hydration and sleep support recovery",
        "category": "Lifestyle",
        "body": "Drink water through the day and aim for consistent sleep. Soft tissue and joint recovery happen between sessions, not only during them.",
    },
    {
        "id": "ht6",
        "title": "Ice vs heat",
        "category": "Self-care",
        "body": "Use a cold pack for 10–15 minutes if a joint is swollen after activity. Use gentle heat for general stiffness when there is no new swelling. Never apply either directly to skin.",
    },
    {
        "id": "ht7",
        "title": "Posture during sitting work",
        "category": "Daily living",
        "body": "Change position every 30–40 minutes. Keep feet supported, hips slightly higher than knees if comfortable, and avoid slumping the lower back for long periods.",
    },
    {
        "id": "ht8",
        "title": "When to seek urgent care",
        "category": "Safety",
        "body": "Chest pain, difficulty breathing, sudden severe swelling, loss of sensation, or inability to bear weight are medical emergencies. Call local emergency services — do not wait for app approval.",
    },
]

# Standard default demo exercises with video previews if missing in DB
DEFAULT_DEMO_EXERCISES = [
    {
        "id": "ex_knee_ext",
        "name": "Seated Knee Extension",
        "description": "Slowly straighten the knee to strengthen the quadriceps. Hold for 2 seconds at the top.",
        "target_joint": "Knee",
        "target_rom": 120,
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "demo_video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "instructions": "Sit tall on a chair. Straighten your leg fully, hold briefly, then lower with control."
    },
    {
        "id": "ex_slr",
        "name": "Straight Leg Raise",
        "description": "Lie flat on your back, lock your knee straight, and lift the leg to 45 degrees.",
        "target_joint": "Knee / Hip",
        "target_rom": 45,
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
        "demo_video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
        "instructions": "Tighten your thigh muscles and raise your leg without bending the knee."
    },
    {
        "id": "ex_hip_abd",
        "name": "Side-Lying Hip Abduction",
        "description": "Strengthen gluteus medius for hip and pelvic stability.",
        "target_joint": "Hip",
        "target_rom": 40,
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
        "demo_video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
        "instructions": "Lie on your side with legs straight. Raise the top leg toward the ceiling smoothly."
    }
]

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="PhysioFlex API", version="1.1.0")

_default_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()] or _default_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(ml_router)

@app.get("/service-worker.js", include_in_schema=False)
async def pwa_service_worker():
    return FileResponse(
        str(BASE_DIR / "static" / "sw.js"),
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# Safe extraction helpers to prevent 'TokenData' attribute errors
def _get_user_display_name(user: TokenData) -> str:
    db = get_db()
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if uid:
        rec = _user_record(db, uid)
        if rec and rec.get("name"):
            return rec["name"]
    return (
        getattr(user, "name", None)
        or getattr(user, "username", None)
        or getattr(user, "email", "User").split("@")[0].capitalize()
    )

def _get_user_email(user: TokenData) -> str:
    return getattr(user, "email", "") or getattr(user, "sub", "") or "user@physioflex.com"


# ---------- Real-time connection manager ----------
class ConnectionManager:
    def __init__(self):
        self.by_role: Dict[str, list] = {"doctor": [], "physiotherapist": [], "patient": [], "admin": []}
        self.by_patient: Dict[str, list] = {}

    async def connect(self, websocket: WebSocket, role: str, patient_id: str = None):
        await websocket.accept()
        self.by_role.setdefault(role, []).append(websocket)
        if patient_id:
            self.by_patient.setdefault(patient_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, role: str, patient_id: str = None):
        if role in self.by_role and websocket in self.by_role[role]:
            self.by_role[role].remove(websocket)
        if patient_id and patient_id in self.by_patient and websocket in self.by_patient[patient_id]:
            self.by_patient[patient_id].remove(websocket)

    async def broadcast_roles(self, roles: list, message: dict):
        dead = []
        for role in roles:
            for ws in list(self.by_role.get(role, [])):
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append((role, ws))
        for role, ws in dead:
            if ws in self.by_role.get(role, []):
                self.by_role[role].remove(ws)

    async def broadcast_patient(self, patient_id: str, message: dict):
        for ws in list(self.by_patient.get(patient_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@app.on_event("startup")
async def startup():
    seed_if_empty()
    print("PhysioFlex 1.1 started")
    print("  admin@physioflex.com  / password123")
    print("  doctor@physioflex.com / password123")
    print("  physio@physioflex.com / password123")
    print("  patient@physioflex.com / password123")


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    age: Optional[int] = None
    gender: Optional[str] = None
    condition: Optional[str] = ""


SUPPORTED_LANGUAGES = {
    "en", "as", "bn", "brx", "doi", "gu", "hi", "kn", "ks",
    "kok", "mai", "ml", "mni", "mr", "ne", "or", "pa",
    "sa", "sat", "sd", "ta", "te", "ur",
}


class LanguagePreferenceRequest(BaseModel):
    language: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def _user_record(db: dict, user_id: str) -> Optional[dict]:
    return next((x for x in db.get("users", []) if x.get("id") == user_id), None)


def _approval_status(u: Optional[dict]) -> str:
    if not u:
        return "pending"
    if u.get("role") != "patient":
        return "approved"
    return u.get("approval_status") or "approved"


def _to_user_out(u: dict) -> UserOut:
    return UserOut(
        id=u["id"],
        email=u["email"],
        name=u["name"],
        role=u["role"],
        approval_status=_approval_status(u),
        preferred_language=u.get("preferred_language", "en"),
    )


def _is_approved_patient(user: TokenData, db: Optional[dict] = None) -> bool:
    if getattr(user, "role", None) != "patient":
        return True
    data = db if db is not None else get_db()
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    return _approval_status(_user_record(data, uid)) == "approved"


async def require_approved_patient(user: TokenData = Depends(require_role("patient"))) -> TokenData:
    if not _is_approved_patient(user):
        raise HTTPException(status_code=403, detail=PENDING_ACCOUNT_MSG)
    return user


@app.post("/api/auth/register", response_model=LoginResponse)
async def register_patient(body: RegisterRequest):
    """Patients may self-register. Clinical features stay locked until admin approval."""
    name = (body.name or "").strip()
    email = (body.email or "").strip().lower()
    password = body.password or ""
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Please enter your full name")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please enter a valid email address")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    db = get_db()
    if any(u.get("email", "").lower() == email for u in db["users"]):
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    uid = generate_id("pat")
    user = {
        "id": uid,
        "email": email,
        "password": get_password_hash(password),
        "name": name,
        "role": "patient",
        "age": body.age,
        "gender": body.gender,
        "approval_status": "pending",
        "created_at": _now(),
        "active": True,
    }
    db["users"].append(user)
    db["patients"].append({
        "id": uid,
        "user_id": uid,
        "name": name,
        "age": body.age,
        "gender": body.gender,
        "email": email,
        "condition": (body.condition or "").strip(),
        "summary": "",
        "operation": "",
        "reason_of_operation": "",
        "surgery_date": None,
        "doctor_id": None,
        "physio_id": None,
        "current_pain": 0,
        "current_rom": 0,
        "target_rom": 120,
        "adherence_percent": 0,
        "status": "pending_approval",
        "created_at": _now(),
        "updated_at": _now(),
    })
    save_db(db)
    await manager.broadcast_roles(["admin"], {
        "event": "patient_registration",
        "patient_id": uid,
        "message": f"New patient registration: {name} ({email}) — awaiting approval",
    })
    token = create_access_token({"sub": user["id"], "role": user["role"], "email": user["email"], "name": user["name"]})
    return LoginResponse(access_token=token, user=_to_user_out(user))


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    db = get_db()
    email = (body.email or "").strip().lower()
    user = next((u for u in db["users"] if u.get("email", "").lower() == email), None)
    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("role") == "patient" and _approval_status(user) == "rejected":
        raise HTTPException(status_code=403, detail=REJECTED_ACCOUNT_MSG)
    token = create_access_token(
        {"sub": user["id"], "role": user["role"], "email": user["email"], "name": user.get("name", "")}
    )
    return LoginResponse(access_token=token, user=_to_user_out(user))


@app.get("/api/auth/me", response_model=UserOut)
async def me(user: TokenData = Depends(get_current_user)):
    db = get_db()
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    u = _user_record(db, uid)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.get("role") == "patient" and _approval_status(u) == "rejected":
        raise HTTPException(status_code=403, detail=REJECTED_ACCOUNT_MSG)
    return _to_user_out(u)


@app.get("/api/auth/language")
async def get_language_preference(user: TokenData = Depends(get_current_user)):
    db = get_db()
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    account = _user_record(db, uid)
    if not account:
        raise HTTPException(status_code=404, detail="User not found")
    language = account.get("preferred_language", "en")
    if language not in SUPPORTED_LANGUAGES:
        language = "en"
    return {
        "language": language,
        "supported_languages": sorted(SUPPORTED_LANGUAGES)
    }


@app.put("/api/auth/language")
async def set_language_preference(
    body: LanguagePreferenceRequest,
    user: TokenData = Depends(get_current_user)
):
    language = body.language.strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported language code"
        )
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail="Unable to identify current user"
        )
    updated = update_user_language(uid, language)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "ok": True,
        "language": language
    }


@app.get("/api/health-tips")
async def list_health_tips(user: TokenData = Depends(get_current_user)):
    return HEALTH_TIPS


# ---------- Exercise catalog with Demo Videos ----------
@app.get("/api/exercises")
async def list_exercises(user: TokenData = Depends(get_current_user)):
    db = get_db()
    exs = db.get("exercises", [])
    if not exs:
        exs = DEFAULT_DEMO_EXERCISES
    # Guarantee every exercise item has a working demo video link
    for i, ex in enumerate(exs):
        if not ex.get("demo_video_url") and not ex.get("video_url"):
            fallback = DEFAULT_DEMO_EXERCISES[i % len(DEFAULT_DEMO_EXERCISES)]["video_url"]
            ex["demo_video_url"] = fallback
            ex["video_url"] = fallback
    return exs


# ---------- Patients CRUD ----------
def _can_access_patient(user: TokenData, patient: dict) -> bool:
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if user.role in ("doctor", "physiotherapist", "admin"):
        return True
    if user.role == "patient":
        return patient.get("user_id") == uid or patient.get("id") == uid
    return False


@app.get("/api/patients")
async def list_patients(user: TokenData = Depends(get_current_user)):
    db = get_db()
    all_patients = db.get("patients", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if user.role in ("doctor", "admin"):
        pts = [p for p in all_patients if p.get("doctor_id") == uid]
        return pts if pts else all_patients
    if user.role == "physiotherapist":
        pts = [p for p in all_patients if p.get("physio_id") == uid]
        return pts if pts else all_patients
    if user.role == "patient":
        return [p for p in all_patients if p.get("user_id") == uid or p.get("id") == uid]
    return []


@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: str, user: TokenData = Depends(get_current_user)):
    db = get_db()
    patient = next((p for p in db["patients"] if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not _can_access_patient(user, patient):
        raise HTTPException(status_code=403, detail="Access denied")
    if user.role in ("doctor", "physiotherapist", "admin"):
        uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
        log_audit_event(
            actor_id=uid,
            actor_name=_get_user_display_name(user),
            actor_role=user.role,
            action="VIEW_PATIENT_RECORD",
            target_id=patient_id,
            details=f"Viewed clinical profile and telemetry of patient {patient.get('name')}"
        )
    return patient


class PatientCreate(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    email: Optional[str] = None
    condition: Optional[str] = ""
    summary: Optional[str] = ""
    operation: Optional[str] = ""
    reason_of_operation: Optional[str] = ""
    surgery_date: Optional[str] = None
    target_rom: Optional[float] = 120
    status: Optional[str] = "active"


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    email: Optional[str] = None
    condition: Optional[str] = None
    summary: Optional[str] = None
    operation: Optional[str] = None
    reason_of_operation: Optional[str] = None
    surgery_date: Optional[str] = None
    current_pain: Optional[int] = None
    current_rom: Optional[float] = None
    target_rom: Optional[float] = None
    adherence_percent: Optional[int] = None
    status: Optional[str] = None
    doctor_id: Optional[str] = None
    physio_id: Optional[str] = None


@app.post("/api/patients")
async def create_patient(
    body: PatientCreate,
    user: TokenData = Depends(require_role("doctor", "physiotherapist", "admin")),
):
    db = get_db()
    db.setdefault("credential_requests", [])
    pid = generate_id("pat")
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    patient = {
        "id": pid,
        "user_id": None,
        "name": body.name,
        "age": body.age,
        "gender": body.gender,
        "email": body.email or "",
        "condition": body.condition or "",
        "summary": body.summary or "",
        "operation": body.operation or "",
        "reason_of_operation": body.reason_of_operation or "",
        "surgery_date": body.surgery_date,
        "doctor_id": uid if user.role == "doctor" else (body.dict().get("doctor_id") or "doc001"),
        "physio_id": uid if user.role == "physiotherapist" else "phy001",
        "current_pain": 0,
        "current_rom": 0,
        "target_rom": body.target_rom or 120,
        "adherence_percent": 0,
        "status": "pending_credentials" if user.role != "admin" else (body.status or "active"),
        "created_at": _now(),
        "updated_at": _now(),
        "requested_by": uid,
        "requested_by_role": user.role,
    }
    if user.role == "doctor":
        patient["doctor_id"] = uid
    db["patients"].append(patient)

    req = {
        "id": generate_id("cr"),
        "type": "patient_credentials",
        "patient_id": pid,
        "patient_name": body.name,
        "email": body.email or "",
        "requested_by": uid,
        "requested_by_role": user.role,
        "status": "pending",
        "created_at": _now(),
    }
    db["credential_requests"].append(req)
    save_db(db)
    await manager.broadcast_roles(["admin", "doctor", "physiotherapist"], {
        "event": "patient_created", "patient_id": pid, "data": patient,
        "message": f"New patient {body.name} – admin must issue login credentials",
    })
    return patient


@app.put("/api/patients/{patient_id}")
async def update_patient(
    patient_id: str,
    body: PatientUpdate,
    user: TokenData = Depends(require_role("doctor", "physiotherapist")),
):
    db = get_db()
    patient = next((p for p in db["patients"] if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not _can_access_patient(user, patient):
        raise HTTPException(status_code=403, detail="Access denied")
    data = body.dict(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            patient[k] = v
    patient["updated_at"] = _now()
    save_db(db)
    append_event("patient_updated", {"patient": patient}, patient_id=patient_id)
    await manager.broadcast_roles(["doctor", "physiotherapist", "patient"], {
        "event": "patient_updated", "patient_id": patient_id, "data": patient,
    })
    return patient


@app.delete("/api/patients/{patient_id}")
async def delete_patient(
    patient_id: str,
    user: TokenData = Depends(require_role("doctor", "physiotherapist")),
):
    db = get_db()
    patient = next((p for p in db["patients"] if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not _can_access_patient(user, patient):
        raise HTTPException(status_code=403, detail="Access denied")
    db["patients"] = [p for p in db["patients"] if p["id"] != patient_id]
    save_db(db)
    append_event("patient_deleted", {"patient_id": patient_id}, patient_id=patient_id)
    await manager.broadcast_roles(["doctor", "physiotherapist"], {
        "event": "patient_deleted", "patient_id": patient_id,
    })
    return {"ok": True, "deleted": patient_id}


# ---------- Assessments ----------
@app.get("/api/patients/{patient_id}/assessments")
async def get_assessments(patient_id: str, user: TokenData = Depends(get_current_user)):
    db = get_db()
    return [a for a in db["assessments"] if a["patient_id"] == patient_id]


class AssessmentCreate(BaseModel):
    pain_score: int
    rom_knee_flexion: float
    rom_knee_extension: float
    notes: str = ""


@app.post("/api/patients/{patient_id}/assessments")
async def create_assessment(
    patient_id: str,
    body: AssessmentCreate,
    user: TokenData = Depends(require_role("physiotherapist")),
):
    db = get_db()
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    assessment = {
        "id": generate_id("asm"),
        "patient_id": patient_id,
        "physio_id": uid,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "pain_score": body.pain_score,
        "rom_knee_flexion": body.rom_knee_flexion,
        "rom_knee_extension": body.rom_knee_extension,
        "notes": body.notes,
        "created_at": _now(),
    }
    db["assessments"].append(assessment)
    for p in db["patients"]:
        if p["id"] == patient_id:
            p["current_pain"] = body.pain_score
            p["current_rom"] = body.rom_knee_flexion
            p["updated_at"] = _now()
            break
    save_db(db)
    await manager.broadcast_roles(["doctor", "physiotherapist"], {
        "event": "assessment_created", "patient_id": patient_id, "data": assessment,
    })
    return assessment


# ---------- Rehab Plans ----------
@app.get("/api/patients/{patient_id}/plans")
async def get_plans(patient_id: str, user: TokenData = Depends(get_current_user)):
    db = get_db()
    return [p for p in db["rehab_plans"] if p["patient_id"] == patient_id]


class ExerciseInPlan(BaseModel):
    exercise_id: str
    name: str
    sets: int = 3
    reps: int = 10
    target_rom: float = 90
    frequency: str = "Daily"
    instructions: str = ""


class PlanCreate(BaseModel):
    title: str = "Rehab plan"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    exercises: List[ExerciseInPlan] = []


class PlanUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    exercises: Optional[List[ExerciseInPlan]] = None


@app.post("/api/patients/{patient_id}/plans")
async def create_plan(
    patient_id: str,
    body: PlanCreate,
    user: TokenData = Depends(require_role("physiotherapist")),
):
    db = get_db()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end_str = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    plan = {
        "id": generate_id("plan"),
        "patient_id": patient_id,
        "physio_id": uid,
        "title": body.title or "Rehab plan",
        "start_date": body.start_date or today_str,
        "end_date": body.end_date or end_str,
        "status": "active",
        "exercises": [e.dict() for e in body.exercises],
        "created_at": _now(),
        "updated_at": _now(),
    }
    db["rehab_plans"].append(plan)
    save_db(db)
    append_event("plan_created", {"plan": plan}, patient_id=patient_id)
    await manager.broadcast_roles(["doctor", "physiotherapist", "patient"], {
        "event": "plan_created", "patient_id": patient_id, "data": plan,
    })
    return plan


@app.put("/api/plans/{plan_id}")
async def update_plan(
    plan_id: str,
    body: PlanUpdate,
    user: TokenData = Depends(require_role("physiotherapist")),
):
    db = get_db()
    plan = next((p for p in db["rehab_plans"] if p["id"] == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    data = body.dict(exclude_unset=True)
    if "exercises" in data and data["exercises"] is not None:
        plan["exercises"] = [e if isinstance(e, dict) else e.dict() for e in data["exercises"]]
        del data["exercises"]
    for k, v in data.items():
        if v is not None:
            plan[k] = v
    plan["updated_at"] = _now()
    save_db(db)
    await manager.broadcast_roles(["doctor", "physiotherapist", "patient"], {
        "event": "plan_updated", "patient_id": plan["patient_id"], "data": plan,
    })
    return plan


@app.delete("/api/plans/{plan_id}")
async def delete_plan(
    plan_id: str,
    user: TokenData = Depends(require_role("physiotherapist")),
):
    db = get_db()
    plan = next((p for p in db["rehab_plans"] if p["id"] == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    pid = plan["patient_id"]
    db["rehab_plans"] = [p for p in db["rehab_plans"] if p["id"] != plan_id]
    save_db(db)
    await manager.broadcast_roles(["doctor", "physiotherapist", "patient"], {
        "event": "plan_deleted", "patient_id": pid, "plan_id": plan_id,
    })
    return {"ok": True}


# ---------- Sessions ----------
@app.get("/api/patients/{patient_id}/sessions")
async def get_sessions(patient_id: str, user: TokenData = Depends(get_current_user)):
    db = get_db()
    sessions = [s for s in db["sessions"] if s["patient_id"] == patient_id]
    sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return sessions


class SessionCreate(BaseModel):
    plan_id: str
    exercise_id: str
    exercise_name: str
    reps_completed: int
    target_reps: int
    sets_completed: int = 1
    max_rom: float
    avg_rom: float
    quality: str = "Fair"
    pain_score: int = 0
    duration_seconds: int = 0
    source: str = "camera"


@app.post("/api/sessions")
async def create_session(
    body: SessionCreate,
    user: TokenData = Depends(require_role("patient", "physiotherapist")),
):
    if user.role == "patient" and not _is_approved_patient(user):
        raise HTTPException(status_code=403, detail=PENDING_ACCOUNT_MSG)
    db = get_db()
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if user.role == "patient":
        patient_id = uid
        pmatch = next((p for p in db["patients"] if p.get("user_id") == uid or p["id"] == uid), None)
        if pmatch:
            patient_id = pmatch["id"]
        assigned_plan = next(
            (p for p in db.get("rehab_plans", []) if str(p.get("id")) == str(body.plan_id)
             and str(p.get("patient_id")) == str(patient_id) and p.get("status", "active") == "active"),
            None,
        )
        if not assigned_plan:
            raise HTTPException(status_code=403, detail="This rehabilitation plan is not assigned to your account or is inactive.")
        assigned_exercises = assigned_plan.get("exercises", [])
        if assigned_exercises and not any(
            str(e.get("exercise_id", e.get("id", ""))) == str(body.exercise_id)
            for e in assigned_exercises if isinstance(e, dict)
        ):
            raise HTTPException(status_code=403, detail="This exercise is not part of the selected rehabilitation plan.")
    else:
        patient_id = "pat001"

    session = {
        "id": generate_id("ses"),
        "patient_id": patient_id,
        "plan_id": body.plan_id,
        "exercise_id": body.exercise_id,
        "exercise_name": body.exercise_name,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "reps_completed": body.reps_completed,
        "target_reps": body.target_reps,
        "sets_completed": body.sets_completed,
        "max_rom": body.max_rom,
        "avg_rom": body.avg_rom,
        "quality": body.quality,
        "pain_score": body.pain_score,
        "duration_seconds": body.duration_seconds,
        "source": body.source,
        "created_at": _now(),
    }
    db["sessions"].append(session)

    for p in db["patients"]:
        if p["id"] == patient_id:
            p["current_pain"] = body.pain_score
            p["current_rom"] = max(p.get("current_rom") or 0, body.max_rom)
            p["updated_at"] = _now()
            break

    total_target = total_done = 0
    for s in db["sessions"]:
        if s["patient_id"] == patient_id:
            total_target += s.get("target_reps", 0) * max(s.get("sets_completed", 1), 1)
            total_done += s.get("reps_completed", 0)
    if total_target > 0:
        for p in db["patients"]:
            if p["id"] == patient_id:
                p["adherence_percent"] = min(100, int((total_done / total_target) * 100))
                break

    save_db(db)
    append_event("session_completed", {"session": session}, patient_id=patient_id)
    await manager.broadcast_roles(["doctor", "physiotherapist"], {
        "event": "session_completed",
        "patient_id": patient_id,
        "data": session,
        "message": f"Patient completed {body.exercise_name}: {body.reps_completed}/{body.target_reps} reps, ROM {body.max_rom}°, quality {body.quality}",
    })
    return session


@app.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: TokenData = Depends(require_role("doctor", "physiotherapist")),
):
    db = get_db()
    ses = next((s for s in db["sessions"] if s["id"] == session_id), None)
    if not ses:
        raise HTTPException(status_code=404, detail="Session not found")
    pid = ses["patient_id"]
    db["sessions"] = [s for s in db["sessions"] if s["id"] != session_id]
    save_db(db)
    await manager.broadcast_roles(["doctor", "physiotherapist"], {
        "event": "session_deleted", "patient_id": pid, "session_id": session_id,
    })
    return {"ok": True}


# ---------- Notes ----------
@app.get("/api/patients/{patient_id}/notes")
async def get_notes(patient_id: str, user: TokenData = Depends(get_current_user)):
    db = get_db()
    return [n for n in db["notes"] if n["patient_id"] == patient_id]


class NoteCreate(BaseModel):
    content: str


@app.post("/api/patients/{patient_id}/notes")
async def create_note(
    patient_id: str,
    body: NoteCreate,
    user: TokenData = Depends(require_role("doctor", "physiotherapist")),
):
    db = get_db()
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    note = {
        "id": generate_id("note"),
        "patient_id": patient_id,
        "author_id": uid,
        "author_role": user.role,
        "content": body.content,
        "created_at": _now(),
    }
    db["notes"].append(note)
    save_db(db)
    await manager.broadcast_roles(["doctor", "physiotherapist", "patient"], {
        "event": "note_added", "patient_id": patient_id, "data": note,
        "message": f"New note on patient record",
    })
    return note


# ---------- Alerts ----------
@app.get("/api/patients/{patient_id}/alerts")
async def get_alerts(patient_id: str, user: TokenData = Depends(get_current_user)):
    db = get_db()
    return [a for a in db["alerts"] if a["patient_id"] == patient_id]


# ---------- Dashboards ----------
@app.get("/api/dashboard/doctor")
async def doctor_dashboard(user: TokenData = Depends(require_role("doctor"))):
    db = get_db()
    all_patients = db.get("patients", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    my_patients = [p for p in all_patients if p.get("doctor_id") == uid]
    seen = set()
    patients = []
    for p in my_patients + all_patients:
        if p.get("id") not in seen:
            seen.add(p.get("id"))
            patients.append(p)
    alerts = [a for a in db.get("alerts", []) if not a.get("resolved") and any(p["id"] == a.get("patient_id") for p in patients)]
    return {
        "patient_count": len(patients),
        "patients": patients,
        "active_alerts": alerts,
        "recent_sessions": sorted(
            [s for s in db.get("sessions", []) if any(p["id"] == s.get("patient_id") for p in patients)],
            key=lambda x: x.get("created_at", ""), reverse=True,
        )[:15],
        "recent_events": sorted(db.get("events", []), key=lambda x: x.get("created_at", ""), reverse=True)[:20],
    }


@app.get("/api/dashboard/physio")
async def physio_dashboard(user: TokenData = Depends(require_role("physiotherapist"))):
    db = get_db()
    all_patients = db.get("patients", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    my_patients = [p for p in all_patients if p.get("physio_id") == uid]
    seen = set()
    patients = []
    for p in my_patients + all_patients:
        if p.get("id") not in seen:
            seen.add(p.get("id"))
            patients.append(p)
    return {
        "patient_count": len(patients),
        "patients": patients,
        "plans": [p for p in db.get("rehab_plans", []) if p.get("physio_id") == uid or any(pt["id"] == p.get("patient_id") for pt in patients)],
        "exercises": db.get("exercises", []),
        "recent_sessions": sorted(
            [s for s in db.get("sessions", []) if any(p["id"] == s.get("patient_id") for p in patients)],
            key=lambda x: x.get("created_at", ""), reverse=True,
        )[:15],
    }


@app.post("/api/patients/{patient_id}/claim")
async def claim_patient(patient_id: str, user: TokenData = Depends(require_role("physiotherapist", "doctor"))):
    db = get_db()
    patient = next((p for p in db.get("patients", []) if p.get("id") == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if user.role == "physiotherapist":
        patient["physio_id"] = uid
    elif user.role == "doctor":
        patient["doctor_id"] = uid
    patient["updated_at"] = _now()
    save_db(db)
    return {"ok": True, "message": "Patient successfully assigned", "patient": patient}


@app.get("/api/dashboard/patient")
async def patient_dashboard(user: TokenData = Depends(require_role("patient"))):
    db = get_db()
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    u = _user_record(db, uid)
    approval = _approval_status(u)
    approved = approval == "approved"
    patient = next((p for p in db["patients"] if p.get("user_id") == uid or p["id"] == uid), None)
    if not patient:
        return {
            "patient": None,
            "active_plans": [],
            "recent_sessions": [],
            "approval_status": approval,
            "access": {"live_sessions": approved, "clinician_interaction": approved},
            "exercises": db.get("exercises", []) if not approved else [],
            "health_tips": HEALTH_TIPS if not approved else [],
        }
    plans = [p for p in db["rehab_plans"] if p["patient_id"] == patient["id"] and p["status"] == "active"]
    sessions = sorted(
        [s for s in db["sessions"] if s["patient_id"] == patient["id"]],
        key=lambda x: x.get("created_at", ""), reverse=True,
    )[:15]
    return {
        "patient": patient,
        "active_plans": plans,
        "recent_sessions": sessions,
        "approval_status": approval,
        "access": {"live_sessions": approved, "clinician_interaction": approved},
        "exercises": db.get("exercises", []),
        "health_tips": HEALTH_TIPS,
    }


@app.get("/api/patients/{patient_id}/progress")
async def get_progress(patient_id: str, user: TokenData = Depends(get_current_user)):
    db = get_db()
    sessions = [s for s in db["sessions"] if s["patient_id"] == patient_id]
    sessions.sort(key=lambda x: x.get("date", ""))
    rom_trend = [{"date": s["date"], "rom": s["max_rom"]} for s in sessions]
    pain_trend = [{"date": s["date"], "pain": s["pain_score"]} for s in sessions]
    return {
        "rom_trend": rom_trend,
        "pain_trend": pain_trend,
        "total_sessions": len(sessions),
    }


# ---------- WebSocket real-time ----------
@app.websocket("/ws/{role}")
async def websocket_role(websocket: WebSocket, role: str):
    await manager.connect(websocket, role)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "subscribe_patient":
                pid = data.get("patient_id")
                if pid:
                    manager.by_patient.setdefault(pid, []).append(websocket)
            elif data.get("type") == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, role)


@app.websocket("/ws/session/{patient_id}")
async def websocket_session(websocket: WebSocket, patient_id: str):
    await manager.connect(websocket, "patient", patient_id)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast_roles(["doctor", "physiotherapist"], {
                "event": "live_metrics",
                "patient_id": patient_id,
                "data": data,
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, "patient", patient_id)


@app.get("/api/admin/credential-requests")
async def list_credential_requests(user: TokenData = Depends(require_role("admin"))):
    db = get_db()
    return sorted(db.get("credential_requests", []), key=lambda x: x.get("created_at", ""), reverse=True)


class ProvisionCredentials(BaseModel):
    email: str
    password: str = "password123"
    name: Optional[str] = None


@app.post("/api/admin/credential-requests/{req_id}/provision")
async def provision_credentials(req_id: str, body: ProvisionCredentials, user: TokenData = Depends(require_role("admin"))):
    db = get_db()
    req = next((r for r in db.get("credential_requests", []) if r["id"] == req_id), None)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if any(u["email"] == body.email for u in db["users"]):
        raise HTTPException(status_code=400, detail="Email already in use")
    uid = req.get("patient_id") or generate_id("pat")
    new_user = {
        "id": uid,
        "email": body.email,
        "password": get_password_hash(body.password or "password123"),
        "name": body.name or req.get("patient_name") or "Patient",
        "role": "patient",
        "created_at": _now(),
        "active": True,
        "approval_status": "approved",
    }
    db["users"].append(new_user)
    for p in db["patients"]:
        if p["id"] == req.get("patient_id"):
            p["user_id"] = uid
            p["email"] = body.email
            p["status"] = "active"
            p["updated_at"] = _now()
            break
    req["status"] = "provisioned"
    req["provisioned_email"] = body.email
    req["updated_at"] = _now()
    save_db(db)
    await manager.broadcast_roles(["admin", "doctor", "physiotherapist"], {
        "event": "credentials_provisioned", "patient_id": req.get("patient_id"),
        "message": f"Login created for {new_user['name']}",
    })
    return {"ok": True, "user": {k: v for k, v in new_user.items() if k != "password"}, "temp_password": body.password}


@app.delete("/api/admin/credential-requests/{req_id}")
async def delete_credential_request(
    req_id: str,
    user: TokenData = Depends(require_role("admin")),
):
    db = get_db()
    requests = db.get("credential_requests", [])
    req = next((r for r in requests if r.get("id") == req_id), None)
    if not req:
        raise HTTPException(status_code=404, detail="Credential request not found")

    db["credential_requests"] = [r for r in requests if r.get("id") != req_id]
    patient_id = req.get("patient_id")
    if patient_id:
        for patient in db.get("patients", []):
            if patient.get("id") == patient_id:
                patient["status"] = "credential_rejected"
                patient["updated_at"] = _now()
                break

    save_db(db)
    await manager.broadcast_roles(
        ["admin", "doctor", "physiotherapist"],
        {
            "event": "credential_request_deleted",
            "patient_id": patient_id,
            "request_id": req_id,
            "message": f"Login request for {req.get('patient_name', 'patient')} was rejected by admin.",
        },
    )
    return {"ok": True, "deleted": req_id, "patient_id": patient_id}


class RegistrationDecision(BaseModel):
    doctor_id: Optional[str] = None
    physio_id: Optional[str] = None
    reason: Optional[str] = None


@app.get("/api/admin/registrations")
async def list_patient_registrations(user: TokenData = Depends(require_role("admin"))):
    db = get_db()
    out = []
    for u in db["users"]:
        if u.get("role") != "patient":
            continue
        status = _approval_status(u)
        if status not in ("pending", "rejected"):
            continue
        patient = next(
            (p for p in db["patients"] if p.get("user_id") == u["id"] or p.get("id") == u["id"]),
            None,
        )
        item = {k: v for k, v in u.items() if k != "password"}
        item["approval_status"] = status
        if patient:
            item["condition"] = patient.get("condition")
            item["patient_status"] = patient.get("status")
        out.append(item)
    out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return out


@app.post("/api/admin/registrations/{user_id}/approve")
async def approve_patient_registration(
    user_id: str,
    body: RegistrationDecision = RegistrationDecision(),
    user: TokenData = Depends(require_role("admin")),
):
    db = get_db()
    u = _user_record(db, user_id)
    if not u or u.get("role") != "patient":
        raise HTTPException(status_code=404, detail="Patient registration not found")
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    u["approval_status"] = "approved"
    u["approved_at"] = _now()
    u["approved_by"] = uid
    for p in db["patients"]:
        if p.get("user_id") == user_id or p.get("id") == user_id:
            p["status"] = "active"
            if body.doctor_id:
                p["doctor_id"] = body.doctor_id
            if body.physio_id:
                p["physio_id"] = body.physio_id
            p["updated_at"] = _now()
            break
    save_db(db)
    await manager.broadcast_roles(["admin", "doctor", "physiotherapist", "patient"], {
        "event": "patient_approved",
        "patient_id": user_id,
        "message": f"{u.get('name')} was approved and can now use live sessions and clinician messaging",
    })
    return {"ok": True, "user": _to_user_out(u)}


@app.post("/api/admin/registrations/{user_id}/reject")
async def reject_patient_registration(
    user_id: str,
    body: RegistrationDecision = RegistrationDecision(),
    user: TokenData = Depends(require_role("admin")),
):
    db = get_db()
    u = _user_record(db, user_id)
    if not u or u.get("role") != "patient":
        raise HTTPException(status_code=404, detail="Patient registration not found")
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    u["approval_status"] = "rejected"
    u["rejected_at"] = _now()
    u["rejected_by"] = uid
    u["rejection_reason"] = (body.reason or "").strip()
    for p in db["patients"]:
        if p.get("user_id") == user_id or p.get("id") == user_id:
            p["status"] = "registration_rejected"
            p["updated_at"] = _now()
            break
    save_db(db)
    await manager.broadcast_roles(["admin"], {
        "event": "patient_rejected",
        "patient_id": user_id,
        "message": f"Registration for {u.get('name')} was declined",
    })
    return {"ok": True, "user": _to_user_out(u)}


# ---------- Admin: user CRUD ----------
class AdminUserCreate(BaseModel):
    email: str
    password: str = "password123"
    name: str
    role: str
    specialty: Optional[str] = None
    license: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None


class AdminUserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    specialty: Optional[str] = None
    license: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    active: Optional[bool] = None


@app.get("/api/admin/users")
async def admin_list_users(user: TokenData = Depends(require_role("admin"))):
    db = get_db()
    out = []
    for u in db["users"]:
        item = {k: v for k, v in u.items() if k != "password"}
        out.append(item)
    return out


@app.post("/api/admin/users")
async def admin_create_user(body: AdminUserCreate, user: TokenData = Depends(require_role("admin"))):
    db = get_db()
    if any(u["email"] == body.email for u in db["users"]):
        raise HTTPException(status_code=400, detail="Email already registered")
    if body.role not in ("admin", "doctor", "physiotherapist", "patient"):
        raise HTTPException(status_code=400, detail="Invalid role")
    uid = generate_id(body.role[:3])
    new_user = {
        "id": uid,
        "email": body.email,
        "password": get_password_hash(body.password or "password123"),
        "name": body.name,
        "role": body.role,
        "created_at": _now(),
        "active": True,
        "approval_status": "approved" if body.role == "patient" else None,
    }
    if body.specialty:
        new_user["specialty"] = body.specialty
    if body.license:
        new_user["license"] = body.license
    if body.age is not None:
        new_user["age"] = body.age
    if body.gender:
        new_user["gender"] = body.gender
    db["users"].append(new_user)

    if body.role == "patient":
        db["patients"].append({
            "id": uid, "user_id": uid, "name": body.name, "age": body.age,
            "gender": body.gender, "email": body.email,
            "condition": "", "summary": "", "operation": "", "reason_of_operation": "",
            "surgery_date": None, "doctor_id": "doc001", "physio_id": "phy001",
            "current_pain": 0, "current_rom": 0, "target_rom": 120, "adherence_percent": 0,
            "status": "active", "created_at": _now(), "updated_at": _now(),
        })
    save_db(db)
    await manager.broadcast_roles(["admin", "doctor", "physiotherapist"], {
        "event": "user_created", "data": {k: v for k, v in new_user.items() if k != "password"},
    })
    return {k: v for k, v in new_user.items() if k != "password"}


@app.put("/api/admin/users/{user_id}")
async def admin_update_user(user_id: str, body: AdminUserUpdate, user: TokenData = Depends(require_role("admin"))):
    db = get_db()
    u = next((x for x in db["users"] if x["id"] == user_id), None)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    data = body.dict(exclude_unset=True)
    if "password" in data and data["password"]:
        u["password"] = get_password_hash(data["password"])
        del data["password"]
    for k, v in data.items():
        if v is not None:
            u[k] = v
    if u["role"] == "patient":
        for p in db["patients"]:
            if p.get("user_id") == user_id or p["id"] == user_id:
                if "name" in data and data["name"]:
                    p["name"] = data["name"]
                if "email" in data and data["email"]:
                    p["email"] = data["email"]
                if "age" in data and data["age"] is not None:
                    p["age"] = data["age"]
                if "gender" in data and data["gender"]:
                    p["gender"] = data["gender"]
                p["updated_at"] = _now()
    save_db(db)
    return {k: v for k, v in u.items() if k != "password"}


@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: str, user: TokenData = Depends(require_role("admin"))):
    db = get_db()
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if user_id == uid:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    u = next((x for x in db["users"] if x["id"] == user_id), None)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    db["users"] = [x for x in db["users"] if x["id"] != user_id]
    if u["role"] == "patient":
        db["patients"] = [p for p in db["patients"] if p.get("user_id") != user_id and p["id"] != user_id]
    save_db(db)
    await manager.broadcast_roles(["admin"], {"event": "user_deleted", "user_id": user_id})
    return {"ok": True, "deleted": user_id}


@app.get("/api/admin/stats")
async def admin_stats(user: TokenData = Depends(require_role("admin"))):
    db = get_db()
    roles = {}
    for u in db["users"]:
        roles[u["role"]] = roles.get(u["role"], 0) + 1
    return {
        "users": len(db["users"]),
        "patients": len(db["patients"]),
        "sessions": len(db["sessions"]),
        "plans": len(db["rehab_plans"]),
        "complaints_open": len([c for c in db.get("complaints", []) if c.get("status") != "resolved"]),
        "pending_registrations": len([
            u for u in db["users"]
            if u.get("role") == "patient" and (u.get("approval_status") or "approved") == "pending"
        ]),
        "by_role": roles,
    }


# ---------- Complaints ----------
class ComplaintCreate(BaseModel):
    against_role: str
    against_name: str = ""
    against_user_id: Optional[str] = None
    category: str = "misconduct"
    subject: str
    description: str
    severity: str = "medium"


@app.get("/api/complaints")
async def list_complaints(user: TokenData = Depends(get_current_user)):
    db = get_db()
    all_c = db.get("complaints", [])
    if user.role == "admin":
        return sorted(all_c, key=lambda x: x.get("created_at", ""), reverse=True)
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    return sorted(
        [c for c in all_c if c.get("filed_by_id") == uid],
        key=lambda x: x.get("created_at", ""), reverse=True,
    )


@app.post("/api/complaints")
async def create_complaint(body: ComplaintCreate, user: TokenData = Depends(get_current_user)):
    db = get_db()
    db.setdefault("complaints", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    complaint = {
        "id": generate_id("cmp"),
        "filed_by_id": uid,
        "filed_by_name": _get_user_display_name(user),
        "filed_by_role": user.role,
        "against_role": body.against_role,
        "against_name": body.against_name,
        "against_user_id": body.against_user_id,
        "category": body.category,
        "subject": body.subject,
        "description": body.description,
        "severity": body.severity,
        "status": "open",
        "admin_notes": "",
        "created_at": _now(),
        "updated_at": _now(),
    }
    db["complaints"].append(complaint)
    save_db(db)
    append_event("complaint_filed", {"complaint_id": complaint["id"], "subject": body.subject}, patient_id=None)
    await manager.broadcast_roles(["admin"], {
        "event": "complaint_filed",
        "data": complaint,
        "message": f"New complaint by {complaint['filed_by_name']} ({user.role}): {body.subject}",
    })
    return complaint


class ComplaintUpdate(BaseModel):
    status: Optional[str] = None
    admin_notes: Optional[str] = None


@app.put("/api/complaints/{complaint_id}")
async def update_complaint(
    complaint_id: str,
    body: ComplaintUpdate,
    user: TokenData = Depends(require_role("admin")),
):
    db = get_db()
    c = next((x for x in db.get("complaints", []) if x["id"] == complaint_id), None)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if body.status is not None:
        c["status"] = body.status
    if body.admin_notes is not None:
        c["admin_notes"] = body.admin_notes
    c["updated_at"] = _now()
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    c["reviewed_by"] = uid
    save_db(db)
    return c


# ---------- Schedules ----------
class ScheduleCreate(BaseModel):
    patient_id: str
    title: str
    schedule_type: str = "exercise"
    datetime: str
    notes: str = ""
    created_by_role: Optional[str] = None


@app.get("/api/schedules")
async def list_schedules(user: TokenData = Depends(get_current_user)):
    db = get_db()
    items = db.get("schedules", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if user.role == "patient":
        return [s for s in items if s.get("patient_id") == uid]
    if user.role == "doctor":
        pids = {p["id"] for p in db["patients"] if p.get("doctor_id") == uid}
        return [s for s in items if s.get("patient_id") in pids]
    if user.role == "physiotherapist":
        pids = {p["id"] for p in db["patients"] if p.get("physio_id") == uid}
        return [s for s in items if s.get("patient_id") in pids]
    return items


@app.post("/api/schedules")
async def create_schedule(body: ScheduleCreate, user: TokenData = Depends(require_role("doctor", "physiotherapist", "admin"))):
    db = get_db()
    db.setdefault("schedules", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    item = {
        "id": generate_id("sch"),
        "patient_id": body.patient_id,
        "title": body.title,
        "schedule_type": body.schedule_type,
        "datetime": body.datetime,
        "notes": body.notes,
        "created_by": uid,
        "created_by_role": user.role,
        "status": "scheduled",
        "created_at": _now(),
    }
    db["schedules"].append(item)
    save_db(db)
    await manager.broadcast_roles(["patient", "doctor", "physiotherapist"], {
        "event": "schedule_created", "patient_id": body.patient_id, "data": item,
        "message": f"New schedule: {body.title} ({body.schedule_type})",
    })
    return item


# ---------- Doctor suggestions to physio ----------
class SuggestionCreate(BaseModel):
    patient_id: str
    operation_type: str = ""
    suggested_exercises: List[str] = []
    recommended_sessions: int = 10
    pain_notes: str = ""
    abnormality_notes: str = ""
    general_notes: str = ""


@app.get("/api/suggestions")
async def list_suggestions(user: TokenData = Depends(get_current_user)):
    db = get_db()
    items = db.get("suggestions", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if user.role == "doctor":
        return [s for s in items if s.get("doctor_id") == uid]
    if user.role == "physiotherapist":
        pids = {p["id"] for p in db["patients"] if p.get("physio_id") == uid}
        return [s for s in items if s.get("patient_id") in pids]
    if user.role == "patient":
        return [s for s in items if s.get("patient_id") == uid]
    return items


@app.post("/api/suggestions")
async def create_suggestion(body: SuggestionCreate, user: TokenData = Depends(require_role("doctor"))):
    db = get_db()
    db.setdefault("suggestions", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    item = {
        "id": generate_id("sug"),
        "patient_id": body.patient_id,
        "doctor_id": uid,
        "operation_type": body.operation_type,
        "suggested_exercises": body.suggested_exercises,
        "recommended_sessions": body.recommended_sessions,
        "pain_notes": body.pain_notes,
        "abnormality_notes": body.abnormality_notes,
        "general_notes": body.general_notes,
        "status": "sent",
        "created_at": _now(),
    }
    db["suggestions"].append(item)
    for p in db["patients"]:
        if p["id"] == body.patient_id:
            if body.operation_type:
                p["operation"] = body.operation_type
            if body.abnormality_notes:
                p["summary"] = (p.get("summary") or "") + " | " + body.abnormality_notes
            p["updated_at"] = _now()
            break
    save_db(db)
    await manager.broadcast_roles(["physiotherapist", "doctor"], {
        "event": "suggestion_created", "patient_id": body.patient_id, "data": item,
        "message": f"Doctor suggestion for patient: {body.operation_type or 'rehab plan'}",
    })
    return item


# ---------- Patient alerts to clinicians ----------
class PatientAlertCreate(BaseModel):
    alert_type: str = "pain"
    message: str
    severity: str = "medium"


@app.get("/api/patient-alerts")
async def list_patient_alerts(user: TokenData = Depends(get_current_user)):
    db = get_db()
    items = db.get("patient_alerts", [])
    patients = db.get("patients", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if user.role == "patient":
        patient = next((p for p in patients if p.get("user_id") == uid or p.get("id") == uid), None)
        valid_ids = {uid}
        if patient:
            valid_ids.add(patient.get("id"))
            valid_ids.add(patient.get("user_id"))
        return [a for a in items if a.get("patient_id") in valid_ids]
    if user.role == "doctor":
        pids = {p["id"] for p in patients if p.get("doctor_id") == uid}
        return [a for a in items if a.get("patient_id") in pids or any(p.get("user_id") == a.get("patient_id") and p.get("id") in pids for p in patients)]
    if user.role == "physiotherapist":
        pids = {p["id"] for p in patients if p.get("physio_id") == uid}
        return [a for a in items if a.get("patient_id") in pids or any(p.get("user_id") == a.get("patient_id") and p.get("id") in pids for p in patients)]
    return items


@app.post("/api/patient-alerts")
async def create_patient_alert(body: PatientAlertCreate, user: TokenData = Depends(require_approved_patient)):
    try:
        db = get_db()
        db.setdefault("patient_alerts", [])
        uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
        patient_record = next((p for p in db.get("patients", []) if p.get("user_id") == uid or p.get("id") == uid), None)
        canonical_patient_id = patient_record.get("id") if patient_record else uid
        item = {
            "id": generate_id("pal"),
            "patient_id": canonical_patient_id,
            "patient_user_id": uid,
            "alert_type": body.alert_type,
            "message": body.message,
            "severity": body.severity,
            "status": "open",
            "created_at": _now(),
        }
        persist_patient_alert(item)
        await manager.broadcast_roles(["doctor", "physiotherapist"], {
            "event": "patient_alert", "patient_id": canonical_patient_id, "data": item,
            "message": f"Patient alert ({body.alert_type}): {body.message[:80]}",
        })
        return item
    except Exception:
        import logging
        logging.getLogger("physioflex").exception("Failed to create patient alert")
        raise HTTPException(status_code=500, detail="Could not save the alert.")


# ---------- Live session booking ----------
class BookingCreate(BaseModel):
    with_role: str
    preferred_datetime: str
    reason: str = ""
    notes: str = ""


@app.get("/api/bookings")
async def list_bookings(user: TokenData = Depends(get_current_user)):
    db = get_db()
    items = db.get("bookings", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if user.role == "patient":
        return [b for b in items if b.get("patient_id") == uid]
    if user.role in ("doctor", "physiotherapist"):
        return [b for b in items if b.get("with_role") == user.role or b.get("assigned_to") == uid]
    return items


@app.post("/api/bookings")
async def create_booking(body: BookingCreate, user: TokenData = Depends(require_approved_patient)):
    db = get_db()
    db.setdefault("bookings", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    item = {
        "id": generate_id("bk"),
        "patient_id": uid,
        "with_role": body.with_role,
        "preferred_datetime": body.preferred_datetime,
        "reason": body.reason,
        "notes": body.notes,
        "status": "requested",
        "created_at": _now(),
    }
    db["bookings"].append(item)
    save_db(db)
    roles = ["doctor"] if body.with_role == "doctor" else ["physiotherapist"]
    await manager.broadcast_roles(roles + ["patient"], {
        "event": "booking_requested", "patient_id": uid, "data": item,
        "message": f"Live session requested with {body.with_role}",
    })
    return item


class BookingUpdate(BaseModel):
    status: str
    assigned_to: Optional[str] = None
    meeting_link: Optional[str] = None


@app.put("/api/bookings/{booking_id}")
async def update_booking(booking_id: str, body: BookingUpdate, user: TokenData = Depends(require_role("doctor", "physiotherapist", "admin"))):
    db = get_db()
    b = next((x for x in db.get("bookings", []) if x["id"] == booking_id), None)
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    b["status"] = body.status
    if body.assigned_to:
        b["assigned_to"] = body.assigned_to
    if body.meeting_link:
        b["meeting_link"] = body.meeting_link
    b["updated_at"] = _now()
    save_db(db)
    await manager.broadcast_roles(["patient", "doctor", "physiotherapist"], {
        "event": "booking_updated", "patient_id": b["patient_id"], "data": b,
    })
    return b


# ---------- Voice messages ----------
class VoiceMessageCreate(BaseModel):
    to_role: str = "physiotherapist"
    to_user_id: Optional[str] = None
    audio_base64: Optional[str] = None
    transcript: str = ""
    duration_seconds: int = 0


@app.get("/api/voice-messages")
async def list_voice_messages(user: TokenData = Depends(get_current_user)):
    db = get_db()
    items = db.get("voice_messages", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    out = []
    for m in items:
        if m.get("from_id") == uid:
            out.append(m)
        elif m.get("to_user_id") == uid:
            out.append(m)
        elif m.get("to_role") == user.role:
            out.append(m)
    clean = []
    for m in out:
        c = dict(m)
        if c.get("audio_base64") and len(c["audio_base64"]) > 200:
            c["has_audio"] = True
            c["audio_base64"] = None
        clean.append(c)
    return sorted(clean, key=lambda x: x.get("created_at", ""), reverse=True)


@app.post("/api/voice-messages")
async def create_voice_message(body: VoiceMessageCreate, user: TokenData = Depends(get_current_user)):
    if user.role == "patient" and not _is_approved_patient(user):
        raise HTTPException(status_code=403, detail=PENDING_ACCOUNT_MSG)
    db = get_db()
    db.setdefault("voice_messages", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    transcript = (body.transcript or "").strip()
    audio = body.audio_base64
    if audio and len(audio) > 400000:
        audio = None
        if not transcript:
            transcript = "[Voice clip too large – please type a short message]"
    if not transcript and not audio:
        raise HTTPException(status_code=400, detail="Please record audio or type a message")
    item = {
        "id": generate_id("vm"),
        "from_id": uid,
        "from_role": user.role,
        "to_role": body.to_role or "physiotherapist",
        "to_user_id": body.to_user_id,
        "audio_base64": audio,
        "transcript": transcript,
        "duration_seconds": body.duration_seconds or 0,
        "created_at": _now(),
    }
    db["voice_messages"].append(item)
    if len(db["voice_messages"]) > 80:
        db["voice_messages"] = db["voice_messages"][-80:]
    save_db(db)
    roles = list({body.to_role, user.role, "doctor", "physiotherapist", "patient"} & {"doctor", "physiotherapist", "patient", "admin"})
    await manager.broadcast_roles(roles, {
        "event": "voice_message",
        "data": {k: v for k, v in item.items() if k != "audio_base64"},
        "message": f"Message from {user.role}: {(transcript or 'voice note')[:60]}",
    })
    return {k: v for k, v in item.items() if k != "audio_base64"}


@app.get("/api/voice-messages/{msg_id}/audio")
async def get_voice_audio(msg_id: str, user: TokenData = Depends(get_current_user)):
    db = get_db()
    m = next((x for x in db.get("voice_messages", []) if x["id"] == msg_id), None)
    if not m:
        raise HTTPException(status_code=404, detail="Message not found")
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    allowed = (
        m.get("from_id") == uid
        or m.get("to_user_id") == uid
        or m.get("to_role") == user.role
        or user.role == "admin"
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Not allowed")
    audio = m.get("audio_base64")
    if not audio:
        raise HTTPException(status_code=404, detail="No audio on this message")
    return {"id": msg_id, "audio_base64": audio, "mime": "audio/webm"}


# ---------- Progress evaluation ----------
@app.get("/api/patients/{patient_id}/evaluation")
async def progress_evaluation(patient_id: str, user: TokenData = Depends(get_current_user)):
    db = get_db()
    patient = next((p for p in db["patients"] if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    sessions = [s for s in db["sessions"] if s["patient_id"] == patient_id]
    sessions.sort(key=lambda x: x.get("created_at", ""))
    if not sessions:
        return {
            "patient_id": patient_id,
            "evaluation": "Insufficient data",
            "score": 0,
            "rom_improvement": 0,
            "pain_trend": "unknown",
            "adherence": patient.get("adherence_percent", 0),
            "recommendations": ["Complete more exercise sessions for evaluation."],
            "session_count": 0,
        }
    first_rom = sessions[0].get("max_rom") or 0
    last_rom = sessions[-1].get("max_rom") or 0
    first_pain = sessions[0].get("pain_score", 5)
    last_pain = sessions[-1].get("pain_score", 5)
    good_q = sum(1 for s in sessions if s.get("quality") == "Good")
    rom_imp = last_rom - first_rom
    pain_delta = first_pain - last_pain
    adherence = patient.get("adherence_percent", 0)
    score = min(100, max(0, int(
        adherence * 0.4 +
        min(40, max(0, rom_imp) * 2) +
        min(20, max(0, pain_delta) * 5) +
        (good_q / max(len(sessions), 1)) * 20
    )))
    if score >= 75:
        evaluation = "Excellent progress"
    elif score >= 55:
        evaluation = "Good progress"
    elif score >= 35:
        evaluation = "Moderate progress – continue plan"
    else:
        evaluation = "Limited progress – review recommended"
    recs = []
    if rom_imp < 5:
        recs.append("ROM gains are small; consider adjusting exercise intensity.")
    if last_pain >= 6:
        recs.append("Pain remains elevated; clinical review advised.")
    if adherence < 60:
        recs.append("Improve session adherence.")
    if good_q / max(len(sessions), 1) < 0.5:
        recs.append("Focus on movement quality; reduce compensation.")
    if not recs:
        recs.append("Maintain current plan and reassess in 1–2 weeks.")
    return {
        "patient_id": patient_id,
        "evaluation": evaluation,
        "score": score,
        "rom_improvement": round(rom_imp, 1),
        "pain_trend": "improving" if pain_delta > 0 else ("worsening" if pain_delta < 0 else "stable"),
        "adherence": adherence,
        "session_count": len(sessions),
        "good_quality_ratio": round(good_q / len(sessions), 2),
        "recommendations": recs,
    }


# ---------- HTML pages ----------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@app.get("/doctor", response_class=HTMLResponse)
async def doctor_portal(request: Request):
    return templates.TemplateResponse(request, "doctor.html")


@app.get("/physio", response_class=HTMLResponse)
async def physio_portal(request: Request):
    return templates.TemplateResponse(request, "physio.html")


@app.get("/patient", response_class=HTMLResponse)
async def patient_portal(request: Request):
    return templates.TemplateResponse(request, "patient.html")


@app.get("/patient/exercise", response_class=HTMLResponse)
async def exercise_page(request: Request):
    return templates.TemplateResponse(request, "exercise.html")


@app.get("/chat", response_class=HTMLResponse)
async def smart_chat_page(request: Request):
    return templates.TemplateResponse(request, "chat.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_portal(request: Request):
    return templates.TemplateResponse(request, "admin.html")

@app.get("/movement-analysis", response_class=HTMLResponse)
async def movement_analysis_page(request: Request):
    info = ml_service.get_status_info()
    return templates.TemplateResponse(
        request,
        "movement_analysis.html",
        {
            "model_name": info["model_name"],
            "accuracy": info["accuracy"],
            "features_count": info["features_required"],
        }
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "PhysioFlex", "version": "1.1.2-video-fix"}


# ---------- Smart Chat ----------
class SmartChatRequest(BaseModel):
    message: str
    patient_id: Optional[str] = None


def _chat_patient_for_user(db: dict, user: TokenData, requested_patient_id: Optional[str]) -> Optional[dict]:
    patients = db.get("patients", [])
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if user.role == "patient":
        return next((p for p in patients if p.get("user_id") == uid or p.get("id") == uid), None)
    if user.role in ("doctor", "physiotherapist"):
        if not requested_patient_id:
            return None
        patient = next((p for p in patients if p.get("id") == requested_patient_id), None)
        if not patient or not _can_access_patient(user, patient):
            raise HTTPException(status_code=403, detail="You do not have access to this patient")
        return patient
    if user.role == "admin":
        return None
    raise HTTPException(status_code=403, detail="Smart Chat is not enabled for this role")


def _chat_context_tools(db: dict, user: TokenData, patient: Optional[dict], message: str) -> dict:
    if not patient:
        return {"available_tools": ["exercise_guidance"], "patient_context": None}
    pid = patient.get("id")
    sessions = [s for s in db.get("sessions", []) if s.get("patient_id") == pid]
    sessions.sort(key=lambda x: x.get("created_at", x.get("date", "")))
    plans = [p for p in db.get("rehab_plans", []) if p.get("patient_id") == pid]
    assessments = [a for a in db.get("assessments", []) if a.get("patient_id") == pid]
    alerts = [a for a in db.get("patient_alerts", []) if a.get("patient_id") in (pid, patient.get("user_id"))]
    recent_sessions = sessions[-5:]
    recent_assessments = assessments[-5:]
    return {
        "tools_used": ["get_recovery_summary", "get_rehab_plans", "get_clinical_alerts"],
        "patient_context": {
            "patient_name": patient.get("name", "Patient"),
            "condition": patient.get("condition", "Not recorded"),
            "current_pain": patient.get("current_pain"),
            "current_rom": patient.get("current_rom"),
            "session_count": len(sessions),
            "recent_sessions": [{k: s.get(k) for k in ("date", "pain_score", "max_rom", "exercise_name", "quality", "notes") if s.get(k) is not None} for s in recent_sessions],
            "recent_assessments": [{k: a.get(k) for k in ("date", "pain_score", "rom_knee_flexion", "rom_knee_extension", "notes") if a.get(k) is not None} for a in recent_assessments],
            "rehab_plans": [{k: p.get(k) for k in ("title", "status", "start_date", "end_date", "exercises") if p.get(k) is not None} for p in plans[-5:]],
            "open_alerts": [{k: a.get(k) for k in ("alert_type", "message", "severity", "status", "created_at") if a.get(k) is not None} for a in alerts if a.get("status", "open") == "open"][-10:],
        },
    }

def _is_pain_concern(message: str) -> tuple[bool, str]:
    text = message.lower()
    emergency_terms = ("chest pain", "can't breathe", "cannot breathe", "difficulty breathing", "fainted", "unconscious", "severe bleeding")
    urgent_terms = ("severe pain", "sudden pain", "pain is getting worse", "pain getting worse", "worsening pain", "swelling increased", "numbness", "can't move", "cannot move")
    if any(term in text for term in emergency_terms) or any(term in text for term in urgent_terms):
        return True, "high"
    if ("pain" in text and any(x in text for x in ("worse", "increased", "increasing", "more pain", "7/10", "8/10", "9/10", "10/10"))):
        return True, "medium"
    return False, ""


def _gemini_reply(prompt: str) -> Optional[str]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    models_to_try = [
        os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip(),
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-pro-latest",
        "gemini-1.5-flash",
    ]
    models_to_try = [m for i, m in enumerate(models_to_try) if m and m not in models_to_try[:i]]

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 800}
        }
        req = URLRequest(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(req, timeout=14) as response:
                data = json.loads(response.read().decode("utf-8"))
            candidate = data.get("candidates", [{}])[0]
            text = "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", [])).strip()
            if text:
                return text
        except Exception:
            continue
    return None


def _fallback_chat_reply(message: str, role: str, context: dict) -> str:
    text = message.lower().strip()
    patient = context.get("patient_context") or {}
    p_name = patient.get("patient_name") or "Patient"
    condition = patient.get("condition") or "Rehabilitation"
    cur_pain = patient.get("current_pain")
    cur_rom = patient.get("current_rom")

    if any(k in text for k in ("knee extension", "seated knee")):
        return (
            "🦵 **Seated Knee Extension Technique:**\n\n"
            "1. Sit upright on a stable chair.\n"
            "2. Straighten your knee until your leg is extended horizontally (Target ROM: 110°–120°).\n"
            "3. Contract your quadriceps firmly and hold for 2 seconds at the top.\n"
            "4. Slowly lower your foot down over 3 seconds."
        )

    if any(k in text for k in ("ice vs heat", "cold or hot", "when to use ice")):
        return (
            "🧊🔥 **Ice vs. Heat Guidelines:**\n\n"
            "• **Use ICE (10–15 min):** After exercise or if joint feels warm, tender, or swollen.\n"
            "• **Use HEAT (15–20 min):** For general stiffness before stretching. Never use on swollen areas."
        )

    return (
        f"💡 **Rehabilitation Advisory for {p_name} ({condition}):**\n\n"
        f"Your recorded range of motion is **{str(cur_rom) + '°' if cur_rom is not None else 'not recorded'}** "
        f"and pain score is **{str(cur_pain) + '/10' if cur_pain is not None else 'not recorded'}**.\n"
        "Follow your clinician-approved plan. If sharp or worsening pain occurs, stop and contact your care team."
    )


def _agentic_tool_workflow(message: str, role: str, patient: Optional[dict], db: dict, allow_patient_tools: bool = True) -> dict:
    """
    Bounded multi-agent workflow:
    1) coordinator classifies the request and chooses a specialist agent;
    2) specialist selects allow-listed read-only tools;
    3) the language model synthesizes tool results.
    Clinical writes remain clinician-controlled.
    """
    text = (message or "").lower()
    pid = str(patient.get("id")) if patient else None
    agent = "Rehabilitation Guide"
    planned_tools = []
    approval_required = False

    safety_terms = ("pain", "swelling", "numb", "dizzy", "worse", "injury", "cannot move", "can't move")
    exercise_terms = ("exercise", "posture", "rom", "range of motion", "movement", "reps", "form", "technique")
    report_terms = ("report", "assessment", "clinical summary", "progress summary")
    plan_terms = ("change plan", "update plan", "add exercise", "remove exercise", "prescribe", "treatment plan")

    if any(term in text for term in safety_terms):
        agent = "Safety & Symptom Monitor"
        planned_tools = ["get_recent_sessions", "get_open_alerts", "get_recovery_summary"]
    elif any(term in text for term in plan_terms):
        agent = "Care Plan Coordinator"
        planned_tools = ["get_active_rehab_plan", "get_recent_sessions"]
        approval_required = True
    elif any(term in text for term in report_terms):
        agent = "Clinical Report Assistant"
        planned_tools = ["get_recovery_summary", "get_recent_sessions", "get_active_rehab_plan"]
        approval_required = True
    elif any(term in text for term in exercise_terms):
        agent = "Movement & Exercise Coach"
        planned_tools = ["get_active_rehab_plan", "get_recent_sessions", "get_recovery_summary"]
    elif patient:
        agent = "Recovery Progress Analyst"
        planned_tools = ["get_recovery_summary", "get_recent_sessions", "get_open_alerts"]

    # Explicit, role-scoped read-only tools. No model-generated arbitrary database queries.
    result = {"patient_context_available": bool(patient)}
    tools_executed = []
    if patient and pid and allow_patient_tools:
        sessions = [s for s in db.get("sessions", []) if str(s.get("patient_id")) == pid]
        sessions.sort(key=lambda s: s.get("created_at", s.get("date", "")))
        plans = [p for p in db.get("rehab_plans", []) if str(p.get("patient_id")) == pid]
        alerts = [a for a in db.get("patient_alerts", []) if str(a.get("patient_id")) in (pid, str(patient.get("user_id")))]
        if "get_recovery_summary" in planned_tools:
            result["recovery_summary"] = {
                "patient_name": patient.get("name"),
                "condition": patient.get("condition") or patient.get("injury"),
                "recovery_stage": patient.get("recovery_stage"),
                "current_pain": patient.get("current_pain", patient.get("pain_level")),
                "current_rom": patient.get("current_rom"),
                "adherence_percent": patient.get("adherence_percent"),
                "session_count": len(sessions),
            }
            tools_executed.append("get_recovery_summary")
        if "get_recent_sessions" in planned_tools:
            result["recent_sessions"] = [
                {k: s.get(k) for k in ("date", "exercise_name", "reps_completed", "target_reps", "max_rom", "avg_rom", "quality", "pain_score") if s.get(k) is not None}
                for s in sessions[-5:]
            ]
            tools_executed.append("get_recent_sessions")
        if "get_active_rehab_plan" in planned_tools:
            result["active_rehab_plans"] = [
                {k: p.get(k) for k in ("title", "status", "start_date", "end_date", "exercises") if p.get(k) is not None}
                for p in plans if p.get("status", "active") == "active"
            ]
            tools_executed.append("get_active_rehab_plan")
        if "get_open_alerts" in planned_tools:
            result["open_alerts"] = [
                {k: a.get(k) for k in ("alert_type", "message", "severity", "created_at") if a.get(k) is not None}
                for a in alerts if a.get("status", "open") == "open"
            ][-10:]
            tools_executed.append("get_open_alerts")
    elif patient and not allow_patient_tools:
        result["consent_note"] = "Automated decision-support consent is not enabled. Patient-specific AI tools were not run and clinical context was not sent to the external language model."

    # Patients cannot request clinician-only report drafting for another patient.
    if agent == "Clinical Report Assistant" and role == "patient":
        result["permission_note"] = "Patients can view and download published reports; only the treating doctor can author a clinical evaluation."
        approval_required = False
    if agent in ("Clinical Report Assistant", "Care Plan Coordinator") and role not in ("doctor", "physiotherapist", "admin"):
        result["permission_note"] = "A clinician must review and approve clinical plan/report changes."
        approval_required = False

    return {
        "agent": agent,
        "agent_plan": planned_tools,
        "tools_executed": tools_executed,
        "tool_results": result,
        "human_approval_required": approval_required,
    }


@app.post("/api/chat/message")
async def smart_chat_message(body: SmartChatRequest, user: TokenData = Depends(get_current_user)):
    if user.role not in ("patient", "doctor", "physiotherapist", "admin"):
        raise HTTPException(status_code=403, detail="Smart Chat is not enabled for this role")
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be empty")
    if len(message) > 2000:
        raise HTTPException(status_code=413, detail="Message is too long (maximum 2000 characters)")
    db = get_db()
    patient = _chat_patient_for_user(db, user, body.patient_id)
    context = _chat_context_tools(db, user, patient, message)
    consent_record = next(
        (c for c in db.get("consent_settings", []) if patient and str(c.get("patient_id")) == str(patient.get("id"))),
        None,
    )
    ai_context_allowed = bool(consent_record and consent_record.get("automated_decision_support") is True)
    agent_trace = _agentic_tool_workflow(message, user.role, patient, db, allow_patient_tools=(not patient or ai_context_allowed))
    if patient and agent_trace["tools_executed"]:
        uid_for_audit = getattr(user, "user_id", None) or getattr(user, "sub", None)
        log_audit_event(
            actor_id=uid_for_audit,
            actor_name=_get_user_display_name(user),
            actor_role=user.role,
            action="AGENT_READ_ONLY_TOOL_WORKFLOW",
            target_id=str(patient.get("id")),
            details=f"Agent {agent_trace['agent']} executed: {', '.join(agent_trace['tools_executed'])}",
            consent_verified=ai_context_allowed,
        )
    concern, severity = _is_pain_concern(message)
    alert_created = None
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    if concern and user.role == "patient" and _is_approved_patient(user, db):
        db.setdefault("patient_alerts", [])
        alert_created = {
            "id": generate_id("pal"),
            "patient_id": patient.get("id") if patient else uid,
            "alert_type": "pain" if "pain" in message.lower() else "abnormality",
            "message": message[:500],
            "severity": severity,
            "status": "open",
            "source": "smart_chat",
            "created_at": _now(),
        }
        db["patient_alerts"].append(alert_created)
        save_db(db)
        if patient:
            roles = []
            if patient.get("doctor_id"): roles.append("doctor")
            if patient.get("physio_id"): roles.append("physiotherapist")
            if roles:
                await manager.broadcast_roles(roles, {"event": "smart_chat_alert", "patient_id": patient.get("id"), "alert_id": alert_created["id"], "message": "A patient submitted a symptom concern in Smart Chat."})
    system_prompt = (
        f"You are PhysioFlex Agentic Rehabilitation Assistant. Specialist agent: {agent_trace['agent']}. "
        f"User role: {user.role}. Existing authorized context: {json.dumps(context, ensure_ascii=False)[:5000]}. "
        f"Results from tools you actually executed: {json.dumps(agent_trace['tool_results'], ensure_ascii=False, default=str)[:7000]}. "
        f"Agent plan: {agent_trace['agent_plan']}. "
        "Use only supplied records; explicitly say when a measurement is missing. "
        "Never invent ROM, pain scores, diagnoses, exercise results, or patient history. "
        "Do not diagnose, prescribe, change a treatment plan, create a clinical report, or claim an action was completed. "
        "Clinical plan/report changes require treating-clinician review. "
        f"Message: {message}"
    )
    if patient and not ai_context_allowed:
        reply = (
            "Patient-specific AI analysis is currently disabled because automated decision-support consent "
            "has not been enabled for this record. You can still use general exercise education. "
            "A clinician can review the record directly in the portal."
        )
        # Do not send patient-specific data to the external language model without consent.
    else:
        reply = await asyncio.to_thread(_gemini_reply, system_prompt)
        if not reply:
            reply = _fallback_chat_reply(message, user.role, context)
    return {
        "reply": reply,
        "role": user.role,
        "patient_id": patient.get("id") if patient else None,
        "alert_created": bool(alert_created),
        "agent": agent_trace["agent"],
        "agent_plan": agent_trace["agent_plan"],
        "tools_executed": agent_trace["tools_executed"],
        "human_approval_required": agent_trace["human_approval_required"],
    }


# ---------- Clinical Reports & Video Call ----------
class DoctorReportRequest(BaseModel):
    diagnosis: str
    rom_flexion_extension: str
    pain_evaluation: str
    recovery_stage: str
    clinical_score: str
    recommendations: str
    treatment_plan: str
    doctor_signature: Optional[str] = None


@app.post("/api/patients/{patient_id}/doctor-report")
async def create_doctor_report(patient_id: str, body: DoctorReportRequest, user: TokenData = Depends(get_current_user)):
    if user.role not in ("doctor", "admin"):
        raise HTTPException(status_code=403, detail="Only doctors can create clinical evaluation reports")
    db = get_db()
    patient = next((p for p in db.get("patients", []) if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not _can_access_patient(user, patient):
        raise HTTPException(status_code=403, detail="You do not have access to this patient")

    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    dname = _get_user_display_name(user)
    report = {
        "id": generate_id("rep_doc_"),
        "type": "doctor_evaluation",
        "patient_id": patient_id,
        "patient_name": patient.get("name"),
        "doctor_id": uid,
        "doctor_name": dname,
        "created_at": _now(),
        "diagnosis": body.diagnosis,
        "rom_flexion_extension": body.rom_flexion_extension,
        "pain_evaluation": body.pain_evaluation,
        "recovery_stage": body.recovery_stage,
        "clinical_score": body.clinical_score,
        "recommendations": body.recommendations,
        "treatment_plan": body.treatment_plan,
        "doctor_signature": body.doctor_signature or dname,
    }
    db.setdefault("clinical_reports", []).append(report)
    save_db(db)

    log_audit_event(
        actor_id=uid,
        actor_name=dname,
        actor_role=user.role,
        action="CREATE_DOCTOR_REPORT",
        target_id=patient_id,
        details=f"Dr. {dname} generated clinical report for {patient.get('name')} (Score: {body.clinical_score})"
    )
    await manager.broadcast_patient(patient_id, {
        "event": "doctor_report_created",
        "report_id": report["id"],
        "message": f"🩺 Dr. {dname} published an official Clinical Progress Evaluation Report (Score: {body.clinical_score})."
    })
    return report


class PhysioReportRequest(BaseModel):
    functional_mobility_grade: str
    target_rom_achieved: str
    adherence_score: str
    posture_quality: str
    exercise_prescription: str
    precautions: str
    discharge_readiness: str
    physio_signature: Optional[str] = None


@app.post("/api/patients/{patient_id}/physio-report")
async def create_physio_report(patient_id: str, body: PhysioReportRequest, user: TokenData = Depends(get_current_user)):
    if user.role not in ("physiotherapist", "admin"):
        raise HTTPException(status_code=403, detail="Only physiotherapists can create rehabilitation assessment reports")
    db = get_db()
    patient = next((p for p in db.get("patients", []) if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    pname = _get_user_display_name(user)
    report = {
        "id": generate_id("rep_phy_"),
        "type": "physio_rehab",
        "patient_id": patient_id,
        "patient_name": patient.get("name"),
        "physio_id": uid,
        "physio_name": pname,
        "created_at": _now(),
        "functional_mobility_grade": body.functional_mobility_grade,
        "target_rom_achieved": body.target_rom_achieved,
        "adherence_score": body.adherence_score,
        "posture_quality": body.posture_quality,
        "exercise_prescription": body.exercise_prescription,
        "precautions": body.precautions,
        "discharge_readiness": body.discharge_readiness,
        "physio_signature": body.physio_signature or f"Signed by {pname} (Licensed PT)",
    }
    db.setdefault("clinical_reports", []).append(report)
    save_db(db)

    log_audit_event(
        actor_id=uid,
        actor_name=pname,
        actor_role=user.role,
        action="CREATE_PHYSIO_REPORT",
        target_id=patient_id,
        details=f"PT {pname} framed structured rehab report for {patient.get('name')}"
    )
    return report


@app.get("/api/patients/{patient_id}/clinical-reports")
async def get_clinical_reports(patient_id: str, user: TokenData = Depends(get_current_user)):
    db = get_db()
    patient = next((p for p in db.get("patients", []) if str(p.get("id")) == str(patient_id)), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not _can_access_patient(user, patient):
        raise HTTPException(status_code=403, detail="You do not have access to this patient's reports")
    reports = [r for r in db.get("clinical_reports", []) if str(r.get("patient_id")) == str(patient_id)]
    reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return reports


@app.get("/api/patients/{patient_id}/clinical-reports/{report_id}/pdf")
async def download_clinical_report_pdf(
    patient_id: str,
    report_id: str,
    user: TokenData = Depends(get_current_user),
):
    """Generate a downloadable PDF only after verifying patient/report access."""
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    db = get_db()
    patient = next((p for p in db.get("patients", []) if str(p.get("id")) == str(patient_id)), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not _can_access_patient(user, patient):
        raise HTTPException(status_code=403, detail="You do not have access to this patient's reports")
    report = next((r for r in db.get("clinical_reports", []) if str(r.get("id")) == str(report_id) and str(r.get("patient_id")) == str(patient_id)), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    def safe(value):
        text = str(value if value not in (None, "") else "Not recorded")
        return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    .replace("\n", "<br/>"))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="PFTitle", parent=styles["Title"], textColor=colors.HexColor("#0f766e"), fontSize=17, leading=21, spaceAfter=8))
    styles.add(ParagraphStyle(name="PFSection", parent=styles["Heading2"], textColor=colors.HexColor("#115e59"), fontSize=10, leading=13, spaceBefore=10, spaceAfter=4))
    story = [
        Paragraph("PhysioFlex - Clinical Rehabilitation Report", styles["PFTitle"]),
        Paragraph(f"Report ID: {safe(report.get('id'))} &nbsp;&nbsp; Date: {safe(report.get('created_at'))}", styles["Normal"]),
        Spacer(1, 8),
        Paragraph("Patient and clinician", styles["PFSection"]),
    ]
    meta = [
        ["Patient", safe(patient.get("name")), "Report type", safe(report.get("type"))],
        ["Clinician", safe(report.get("doctor_name") or report.get("physio_name")), "Recovery stage", safe(report.get("recovery_stage") or report.get("discharge_readiness"))],
    ]
    table = Table(meta, colWidths=[25*mm, 60*mm, 28*mm, 60*mm])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f0fdfa")),("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#cbd5e1")),("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),8),("VALIGN",(0,0),(-1,-1),"TOP"),("PADDING",(0,0),(-1,-1),6)]))
    story.extend([table, Paragraph("Clinical findings and plan", styles["PFSection"])])
    fields = (
        [("Diagnosis", "diagnosis"), ("ROM - flexion/extension", "rom_flexion_extension"), ("Pain evaluation", "pain_evaluation"), ("Clinical score", "clinical_score"), ("Recommendations", "recommendations"), ("Treatment plan", "treatment_plan")]
        if report.get("type") == "doctor_evaluation" else
        [("Functional mobility grade", "functional_mobility_grade"), ("Target ROM achieved", "target_rom_achieved"), ("Adherence", "adherence_score"), ("Posture quality", "posture_quality"), ("Exercise prescription", "exercise_prescription"), ("Precautions", "precautions"), ("Discharge readiness", "discharge_readiness")]
    )
    for label, key in fields:
        story.append(Paragraph(safe(label), styles["Heading4"]))
        story.append(Paragraph(safe(report.get(key)), styles["BodyText"]))
        story.append(Spacer(1, 4))
    signature = report.get("doctor_signature") or report.get("physio_signature") or "Clinician signature not recorded"
    story.extend([Spacer(1, 16), Paragraph(f"Clinician: {safe(report.get('doctor_name') or report.get('physio_name'))}", styles["Normal"]), Paragraph(f"Signature: {safe(signature)}", styles["Normal"]), Spacer(1, 12), Paragraph("This is a system-generated summary of information entered by the care team. It is not a certified medical record. Camera-derived estimates are not a substitute for clinical goniometric assessment.", styles["Italic"])])
    doc.build(story)
    buffer.seek(0)
    filename = f"PhysioFlex_Report_{report_id}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/admin/audit-logs")
async def get_audit_logs(user: TokenData = Depends(get_current_user)):
    if user.role not in ("admin", "doctor", "physiotherapist"):
        raise HTTPException(status_code=403, detail="Forbidden")
    db = get_db()
    logs = list(db.get("audit_logs", []))
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs[:200]


class ConsentRequest(BaseModel):
    telemetry_sharing: bool
    automated_decision_support: bool
    video_consultation: bool


@app.post("/api/patients/{patient_id}/consent")
async def update_consent_settings(patient_id: str, body: ConsentRequest, user: TokenData = Depends(get_current_user)):
    db = get_db()
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None)
    consent = {
        "patient_id": patient_id,
        "telemetry_sharing": body.telemetry_sharing,
        "automated_decision_support": body.automated_decision_support,
        "video_consultation": body.video_consultation,
        "updated_at": _now(),
        "updated_by": uid,
    }
    existing = next((c for c in db.get("consent_settings", []) if c.get("patient_id") == patient_id), None)
    if existing:
        existing.update(consent)
    else:
        db.setdefault("consent_settings", []).append(consent)
    save_db(db)
    return consent


@app.get("/api/patients/{patient_id}/consent")
async def get_consent_settings(patient_id: str, user: TokenData = Depends(get_current_user)):
    db = get_db()
    consent = next((c for c in db.get("consent_settings", []) if c.get("patient_id") == patient_id), None)
    if not consent:
        consent = {
            "patient_id": patient_id,
            "telemetry_sharing": True,
            "automated_decision_support": True,
            "video_consultation": True,
            "updated_at": _now(),
        }
    return consent


class VideoCallSignal(BaseModel):
    target_role: Optional[str] = None
    target_patient_id: Optional[str] = None
    room_id: str
    action: str  # "initiate", "accept", "decline", "end"
    caller_name: Optional[str] = None
    caller_role: Optional[str] = None


@app.post("/api/calls/signal")
async def video_call_signal(body: VideoCallSignal, user: TokenData = Depends(get_current_user)):
    """Video call signalling endpoint for WebRTC between Patient, Doctor, and Physio."""
    uid = getattr(user, "user_id", None) or getattr(user, "sub", None) or "usr"
    display_name = _get_user_display_name(user)

    payload = {
        "event": "video_call_signal",
        "action": body.action,
        "room_id": body.room_id,
        "caller_name": body.caller_name or display_name,
        "caller_role": body.caller_role or user.role,
        "caller_id": uid,
        "target_role": body.target_role,
        "target_patient_id": body.target_patient_id,
    }

    # If clinician calls a specific patient:
    if user.role in ("doctor", "physiotherapist") and body.target_patient_id:
        await manager.broadcast_patient(body.target_patient_id, payload)
    # If patient calls doctor/physio:
    elif body.target_role:
        await manager.broadcast_roles([body.target_role], payload)
    elif body.target_patient_id:
        await manager.broadcast_patient(body.target_patient_id, payload)
    else:
        # Fallback broadcast to all clinicians
        await manager.broadcast_roles(["doctor", "physiotherapist"], payload)

    log_audit_event(
        actor_id=uid,
        actor_name=display_name,
        actor_role=user.role,
        action="VIDEO_CALL_" + body.action.upper(),
        target_id=body.target_patient_id or body.target_role or "room",
        details=f"Video consultation action {body.action} in room {body.room_id}"
    )
    return {"status": "signaled", "action": body.action, "room_id": body.room_id}