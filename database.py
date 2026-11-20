"""PhysioFlex persistence layer.

Uses MongoDB Atlas in deployed environments and falls back to the bundled JSON
file for local development when MONGODB_URI is not configured.
"""
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

try:
    from pymongo import MongoClient
except ImportError:  # pragma: no cover
    MongoClient = None

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "db.json"
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
MONGO_DB_NAME = (os.getenv("MONGODB_DB_NAME") or os.getenv("MONGO_DB_NAME") or "physioflex_v3").strip()
_lock = threading.Lock()
_client = None
_mongo_db = None

COLLECTIONS = [
    "users", "patients", "assessments", "rehab_plans", "exercises", "sessions",
    "notes", "alerts", "events", "complaints", "voice_messages", "bookings",
    "patient_alerts", "suggestions", "schedules", "credential_requests",
    "audit_logs", "adaptations", "device_telemetry", "risk_alerts", "consent_settings",
    "clinical_reports",
]

DATASET_EXERCISES = [
    {
        "id": "e1",
        "name": "Extended Leg Raises",
        "body_part": "Hip / Knee",
        "joints": ["right_hip", "right_knee"],
        "description": "Lying supine, raise the extended leg upward smoothly to build hip flexor and quadriceps strength.",
        "dataset_code": "e1",
        "default_sets": 3,
        "default_reps": 10,
        "default_target_rom": 45,
        "video_url": "https://www.youtube-nocookie.com/embed/j6kfn_oB6vA",
        "demo_steps": [
            "Lie flat on a firm rehabilitation mat with the non-exercising knee slightly bent.",
            "Lock the exercising knee straight and flex the toes upward toward your shin.",
            "Raise leg steadily to approximately 45 degrees, pausing 2 seconds at the top.",
            "Lower leg slowly under control without bouncing."
        ]
    },
    {
        "id": "e2",
        "name": "Forward Bending",
        "body_part": "Spine / Hip",
        "joints": ["spine", "hip"],
        "description": "Controlled standing or seated forward bend to safely restore lumbar and hamstring flexibility.",
        "dataset_code": "e2",
        "default_sets": 3,
        "default_reps": 10,
        "default_target_rom": 90,
        "video_url": "https://www.youtube-nocookie.com/embed/Uv_EMv3gq3M",
        "demo_steps": [
            "Stand upright with feet hip-width apart and knees soft (unlocked).",
            "Hinge smoothly from your hips, lengthening your spine forward.",
            "Reach downward only as far as comfortable without rounding the upper back.",
            "Exhale on descent and engage core muscles to return upright."
        ]
    },
    {
        "id": "e3",
        "name": "Straight Lying-Leg Raises",
        "body_part": "Hip / Knee",
        "joints": ["right_hip", "right_knee"],
        "description": "Supine straight-leg raise (SLR) designed to rebuild anterior chain knee stability post-op.",
        "dataset_code": "e3",
        "default_sets": 3,
        "default_reps": 12,
        "default_target_rom": 60,
        "video_url": "https://www.youtube-nocookie.com/embed/7V3YwB2v5K8",
        "demo_steps": [
            "Lie flat on your back, keeping opposite knee bent and foot flat on the mat.",
            "Tighten your thigh muscles to lock the knee completely straight.",
            "Lift the leg smoothly to 60 degrees, holding for 3 seconds.",
            "Slowly lower back down. Avoid arching your lower back."
        ]
    },
    {
        "id": "e4",
        "name": "Side Lying Hip Abduction",
        "body_part": "Hip",
        "joints": ["right_hip"],
        "description": "Side-lying hip abduction targeting gluteus medius to stabilize pelvic tilt and gait.",
        "dataset_code": "e4",
        "default_sets": 3,
        "default_reps": 12,
        "default_target_rom": 40,
        "video_url": "https://www.youtube-nocookie.com/embed/kY3XjUa_YgE",
        "demo_steps": [
            "Lie on your unaffected side with hips and shoulders stacked perpendicular to the floor.",
            "Keep the top leg straight with toes pointing slightly downward.",
            "Raise the top leg upward 35 to 40 degrees without rolling backwards.",
            "Hold 1 second and slowly return to start position."
        ]
    },
    {
        "id": "e5",
        "name": "Alternating Leg Lifts Prone",
        "body_part": "Hip / Lumbar",
        "joints": ["hip", "spine"],
        "description": "Prone alternating leg lifts to gently strengthen posterior glutes and lumbar stabilizers.",
        "dataset_code": "e5",
        "default_sets": 3,
        "default_reps": 10,
        "default_target_rom": 30,
        "video_url": "https://www.youtube-nocookie.com/embed/j6kfn_oB6vA",
        "demo_steps": [
            "Lie face down on the mat with forehead resting on hands.",
            "Engage lower abdomen and squeeze glutes.",
            "Lift one leg 15 to 30 degrees off the mat with knee straight.",
            "Alternate legs rhythmically without rotating the pelvis."
        ]
    },
    {
        "id": "e6",
        "name": "Elbow Flexion",
        "body_part": "Elbow",
        "joints": ["right_elbow"],
        "description": "Controlled elbow flexion for post-injury bicep rehab and elbow joint capsule mobility.",
        "dataset_code": "e6",
        "default_sets": 3,
        "default_reps": 15,
        "default_target_rom": 140,
        "video_url": "https://www.youtube-nocookie.com/embed/2_YI07gVp_U",
        "demo_steps": [
            "Sit tall with your arm relaxed at your side, palm facing forward.",
            "Bend the elbow smoothly, bringing palm toward your shoulder.",
            "Reach full comfortable flexion (target 140 degrees).",
            "Slowly straighten arm back to full extension."
        ]
    },
    {
        "id": "e7",
        "name": "Shoulder Abduction",
        "body_part": "Shoulder",
        "joints": ["right_shoulder"],
        "description": "Standing or seated shoulder abduction to restore glenohumeral range of motion.",
        "dataset_code": "e7",
        "default_sets": 3,
        "default_reps": 12,
        "default_target_rom": 160,
        "video_url": "https://www.youtube-nocookie.com/embed/H5zP9kXG_Y8",
        "demo_steps": [
            "Stand tall with core engaged and arms relaxed by your side.",
            "Raise arm laterally out to the side with thumb pointed upward.",
            "Ascend smoothly toward ear level (target 150-160 degrees).",
            "Lower arm down slowly along the same plane."
        ]
    },
    {
        "id": "e8",
        "name": "Prone Lying Elbow Extension",
        "body_part": "Elbow",
        "joints": ["right_elbow"],
        "description": "Prone elbow extension to strengthen triceps and regain terminal elbow lock.",
        "dataset_code": "e8",
        "default_sets": 3,
        "default_reps": 12,
        "default_target_rom": 0,
        "video_url": "https://www.youtube-nocookie.com/embed/2_YI07gVp_U",
        "demo_steps": [
            "Lie prone or bend forward with upper arm parallel to torso.",
            "Extend elbow backward until arm is completely straight.",
            "Hold contraction for 2 seconds at full extension.",
            "Return to 90 degree bend with controlled tempo."
        ]
    },
    {
        "id": "ex001",
        "name": "Seated Knee Extension",
        "body_part": "Knee",
        "joints": ["right_knee"],
        "description": "Seated open-chain knee extension for quadriceps hypertrophy, patellar tracking, and active ROM.",
        "dataset_code": None,
        "default_sets": 3,
        "default_reps": 12,
        "default_target_rom": 120,
        "video_url": "https://www.youtube-nocookie.com/embed/j6kfn_oB6vA",
        "demo_steps": [
            "Sit upright on a sturdy chair with feet flat on the floor.",
            "Slowly kick the foot upward until knee is fully straightened.",
            "Squeeze the front thigh muscle for 2 seconds at maximum extension.",
            "Lower foot back to starting position over 3 seconds."
        ]
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_db() -> Dict[str, Any]:
    return {key: [] for key in COLLECTIONS}


def _local_load() -> Dict[str, Any]:
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = _empty_db()
        data["exercises"] = DATASET_EXERCISES
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data
    with open(DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    for key in COLLECTIONS:
        data.setdefault(key, [])
    return data


def _local_save(data: Dict[str, Any]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _get_mongo_db():
    global _client, _mongo_db
    if not MONGODB_URI:
        return None
    if MongoClient is None:
        raise RuntimeError("pymongo is required when MONGODB_URI is configured")
    if _mongo_db is None:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
        _mongo_db = _client[MONGO_DB_NAME]
        _client.admin.command("ping")
    return _mongo_db


def _mongo_load() -> Dict[str, Any]:
    db = _get_mongo_db()
    data = _empty_db()
    for collection in COLLECTIONS:
        data[collection] = list(db[collection].find({}, {"_id": 0}))
    return data


def _mongo_save(data: Dict[str, Any]) -> None:
    db = _get_mongo_db()

    for collection in COLLECTIONS:
        coll = db[collection]
        coll.delete_many({})

        rows = data.get(collection) or []

        if rows:
            # Use copies so PyMongo does not add ObjectId values
            # to the dictionaries used by the API response.
            clean_rows = []

            for row in rows:
                document = dict(row)
                document.pop("_id", None)
                clean_rows.append(document)

            coll.insert_many(clean_rows, ordered=False)


def get_db() -> Dict[str, Any]:
    with _lock:
        return _mongo_load() if MONGODB_URI else _local_load()


def save_db(data: Dict[str, Any]) -> None:
    with _lock:
        if MONGODB_URI:
            _mongo_save(data)
        else:
            _local_save(data)


def generate_id(prefix: str = "") -> str:
    return (prefix + str(uuid.uuid4())[:8]) if prefix else str(uuid.uuid4())[:8]


def append_event(event_type: str, payload: dict, patient_id: str = None) -> dict:
    data = get_db()
    event = {
        "id": generate_id("ev"),
        "type": event_type,
        "patient_id": patient_id,
        "payload": payload,
        "created_at": _now(),
    }
    data.setdefault("events", []).append(event)
    data["events"] = data["events"][-200:]
    save_db(data)
    return event


def log_audit_event(
    actor_id: str,
    actor_name: str,
    actor_role: str,
    action: str,
    target_id: str = None,
    details: str = "",
    consent_verified: bool = True
) -> dict:
    data = get_db()
    audit_entry = {
        "id": generate_id("aud_"),
        "timestamp": _now(),
        "actor_id": actor_id or "system",
        "actor_name": actor_name or "System",
        "actor_role": actor_role or "system",
        "action": action,
        "target_id": target_id or "none",
        "details": details,
        "consent_verified": consent_verified,
    }
    data.setdefault("audit_logs", []).append(audit_entry)
    data["audit_logs"] = data["audit_logs"][-500:]  # Keep last 500 audit entries
    save_db(data)
    return audit_entry


def _seed_data() -> Dict[str, Any]:
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd.hash(os.getenv("DEMO_PASSWORD", "password123"))
    data = _empty_db()
    data["users"] = [
        {"id": "adm001", "email": "admin@physioflex.com", "password": hashed, "name": "System Admin", "role": "admin", "created_at": _now()},
        {"id": "doc001", "email": "doctor@physioflex.com", "password": hashed, "name": "Dr. Ananya Sharma", "role": "doctor", "specialty": "Orthopedics", "created_at": _now()},
        {"id": "phy001", "email": "physio@physioflex.com", "password": hashed, "name": "Rahul Mehta", "role": "physiotherapist", "license": "PT-2024-8842", "created_at": _now()},
        {"id": "pat001", "email": "patient@physioflex.com", "password": hashed, "name": "Aarav Patel", "role": "patient", "age": 34, "gender": "Male", "approval_status": "approved", "created_at": _now()},
    ]
    data["exercises"] = DATASET_EXERCISES
    data["patients"] = [{
        "id": "pat001", "user_id": "pat001", "name": "Aarav Patel", "age": 34, "gender": "Male",
        "email": "patient@physioflex.com", "condition": "Post-ACL Reconstruction (Right Knee)",
        "summary": "34M post right ACL reconstruction. Progressing through Phase 2 strengthening and ROM.",
        "operation": "Right ACL Reconstruction (hamstring autograft)", "reason_of_operation": "Complete ACL tear after sports injury with instability.",
        "surgery_date": "2026-07-15", "doctor_id": "doc001", "physio_id": "phy001",
        "current_pain": 3, "current_rom": 115, "target_rom": 135, "adherence_percent": 82,
        "status": "active", "created_at": _now(), "updated_at": _now(),
    }]
    data["assessments"] = [{"id": "asm001", "patient_id": "pat001", "physio_id": "phy001", "date": "2026-09-20", "pain_score": 4, "rom_knee_flexion": 110, "rom_knee_extension": 5, "notes": "Mild swelling. Good quadriceps activation.", "created_at": _now()}]
    data["rehab_plans"] = [{
        "id": "plan001", "patient_id": "pat001", "physio_id": "phy001", "title": "ACL Phase 2 – Strength & ROM",
        "start_date": "2026-09-21", "end_date": "2026-10-21", "status": "active",
        "exercises": [
            {"exercise_id": "ex001", "name": "Seated Knee Extension", "sets": 3, "reps": 12, "target_rom": 120, "frequency": "Daily", "instructions": "Sit upright. Slowly extend knee fully. Hold 2s."},
            {"exercise_id": "e3", "name": "Straight Lying-Leg Raises", "sets": 3, "reps": 12, "target_rom": 60, "frequency": "Daily", "instructions": "Lie on back. Keep knee straight. Raise leg. Hold 3s."},
            {"exercise_id": "e1", "name": "Extended Leg Raises", "sets": 3, "reps": 10, "target_rom": 45, "frequency": "Daily", "instructions": "From dataset e1. Raise extended leg controlled."},
        ], "created_at": _now(), "updated_at": _now(),
    }]
    data["sessions"] = [
        {"id": "ses001", "patient_id": "pat001", "plan_id": "plan001", "exercise_id": "ex001", "exercise_name": "Seated Knee Extension", "date": "2026-09-28", "reps_completed": 11, "target_reps": 12, "sets_completed": 3, "max_rom": 118, "avg_rom": 112, "quality": "Good", "pain_score": 3, "duration_seconds": 245, "source": "camera", "created_at": _now()},
        {"id": "ses002", "patient_id": "pat001", "plan_id": "plan001", "exercise_id": "ex001", "exercise_name": "Seated Knee Extension", "date": "2026-09-27", "reps_completed": 12, "target_reps": 12, "sets_completed": 3, "max_rom": 115, "avg_rom": 109, "quality": "Fair", "pain_score": 4, "duration_seconds": 268, "source": "camera", "created_at": _now()},
    ]
    data["notes"] = [{"id": "note001", "patient_id": "pat001", "author_id": "phy001", "author_role": "physiotherapist", "content": "Patient reporting reduced swelling. ROM improving steadily.", "created_at": _now()}]
    data["alerts"] = [{"id": "alt001", "patient_id": "pat001", "type": "movement", "severity": "medium", "message": "Slight compensatory hip hike during knee extension on 2026-09-27.", "resolved": False, "created_at": _now()}]
    return data


def seed_if_empty() -> None:
    data = get_db()
    if data.get("users"):
        data["exercises"] = DATASET_EXERCISES
        changed = False
        for key in COLLECTIONS:
            if key not in data:
                data[key] = []
                changed = True
        if not any(u.get("role") == "admin" for u in data["users"]):
            from passlib.context import CryptContext
            hashed = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(os.getenv("DEMO_PASSWORD", "password123"))
            data["users"].insert(0, {"id": "adm001", "email": "admin@physioflex.com", "password": hashed, "name": "System Admin", "role": "admin", "created_at": _now()})
            changed = True
        save_db(data)
        return
    save_db(_seed_data())
    print("PhysioFlex database seeded")


def persist_patient_alert(item: Dict[str, Any]) -> None:
    """Persist a single patient alert without replacing every MongoDB collection.

    Replacing all collections for one alert can fail on unrelated documents and can
    overwrite concurrent updates. Use insert_one for Atlas and a locked JSON update locally.
    """
    with _lock:
        if MONGODB_URI:
            db = _get_mongo_db()
            document = dict(item)
            document.pop("_id", None)
            db["patient_alerts"].insert_one(document)
        else:
            data = _local_load()
            data.setdefault("patient_alerts", []).append(dict(item))
            _local_save(data)
def update_user_language(user_id: str, language: str) -> bool:
    """
    Update one user's preferred language.
    Supports both MongoDB and local JSON storage.
    """

    # MongoDB: update only the matching user document.
    # Do not use save_db() here because it rewrites all collections.
    if MONGODB_URI:
        mongo_db = _get_mongo_db()
        if mongo_db is None:
            return False

        result = mongo_db["users"].update_one(
            {"id": user_id},
            {"$set": {"preferred_language": language}}
        )

        return result.matched_count > 0

    # Local JSON database
    with _lock:
        data = _local_load()

        for user in data.get("users", []):
            if user.get("id") == user_id:
                user["preferred_language"] = language
                _local_save(data)
                return True

        return False
