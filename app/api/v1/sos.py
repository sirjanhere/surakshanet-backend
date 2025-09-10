"""
SurakshaNet – Real-Time SOS Alert API for Simhastha 2028 (Production Version with Supabase)

Features:
- Pilgrims or staff can trigger SOS (medical, security, lost, other) via app/kiosk, including GPS, details, optional photo.
- Stores alerts in Supabase (Postgres, real-time DB) for instant dashboard display and analytics.
- Publishes real-time notifications for dashboards and field teams using Supabase Realtime via database triggers or frontend listeners.
- Alerts can be marked as resolved; supports querying live & historical alerts.
- All operations are privacy-first and scalable for real-world deployment.

Tech stack:
- FastAPI (Python backend API)
- Supabase (Postgres, real-time DB)
- Pydantic (validation)
- Python Multipart (for photo upload)
- asyncpg (async Postgres driver)
- python-dotenv (optional, for local env vars)

Dependencies:
- pip install fastapi uvicorn supabase asyncpg pydantic python-multipart python-dotenv

You must set SUPABASE_URL and SUPABASE_KEY in your environment or .env.

Example POST /trigger_sos:
{
  "user_id": "user_123",
  "sos_type": "medical",
  "location": {"lat": 23.1825, "lon": 75.7764},
  "details": "Shortness of breath",
  "photo_url": "https://.../photo.jpg"   # optional
}
"""

import os
import uuid
import time
from fastapi import APIRouter, UploadFile, File, Form, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from fastapi.responses import JSONResponse
from datetime import datetime
from dotenv import load_dotenv

from supabase import create_client, Client

# --- Load environment variables for Supabase ---
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "sos-photos")  # Bucket for photo uploads

if not (SUPABASE_URL and SUPABASE_KEY):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment or .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

# --- Models ---
class Location(BaseModel):
    lat: float
    lon: float

class SOSAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    sos_type: str = Field(..., description="Type of SOS (medical, security, lost, other)")
    location: Location
    details: Optional[str] = None
    photo_url: Optional[str] = None
    status: str = "active"  # "active", "resolved"
    created_at: float = Field(default_factory=lambda: time.time())
    resolved_at: Optional[float] = None

# --- Helper: Upload photo to Supabase Storage ---
def upload_photo_to_supabase(photo: UploadFile) -> str:
    """
    Upload the file to Supabase Storage and return the public URL.
    """
    # Generate unique filename
    filename = f"{uuid.uuid4()}_{photo.filename}"
    # Read file as bytes
    file_bytes = photo.file.read()
    # Upload to Supabase Storage
    res = supabase.storage().from_(SUPABASE_BUCKET).upload(filename, file_bytes, {"content-type": photo.content_type})
    if not res or "Key" not in res:
        raise Exception("Failed to upload photo to Supabase Storage")
    # Generate public URL
    public_url = supabase.storage().from_(SUPABASE_BUCKET).get_public_url(filename)
    return public_url

# --- API: Trigger new SOS ---
@router.post("/trigger_sos")
async def trigger_sos(
    user_id: Optional[str] = Form(None),
    sos_type: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    details: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None)
):
    """
    Endpoint to trigger a new SOS alert.
    Accepts form-data for easy mobile/kiosk integration.
    Optionally uploads a photo (evidence, medical, etc).
    """
    try:
        # Upload photo if present
        photo_url = None
        if photo:
            photo_url = upload_photo_to_supabase(photo)

        alert_id = str(uuid.uuid4())
        created_at = time.time()

        # Insert into Supabase
        insert_data = {
            "alert_id": alert_id,
            "user_id": user_id,
            "sos_type": sos_type,
            "lat": lat,
            "lon": lon,
            "details": details,
            "photo_url": photo_url,
            "status": "active",
            "created_at": created_at,
            "resolved_at": None,
        }
        response = supabase.table("sos_alerts").insert(insert_data).execute()
        if not response or len(response.data) == 0:
            raise Exception("Failed to insert SOS alert in Supabase")

        return JSONResponse(content={
            "status": "success",
            "alert_id": alert_id,
            "message": "SOS triggered successfully. Help is on the way!",
            "alert": insert_data
        })
    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "message": f"Failed to trigger SOS: {str(e)}"
        }, status_code=500)

# --- API: List SOS alerts (for dashboard/ops) ---
@router.get("/alerts")
async def list_sos_alerts(
    active: bool = Query(False, description="If true, show only active (unresolved) alerts"),
    sos_type: Optional[str] = Query(None, description="Filter by SOS type"),
    limit: int = Query(100, description="Max results")
):
    """
    Get all (or only active) SOS alerts.
    For dashboard: use Supabase Realtime listeners for live updates.
    """
    try:
        q = supabase.table("sos_alerts").select("*").order("created_at", desc=True)
        if active:
            q = q.eq("status", "active")
        if sos_type:
            q = q.eq("sos_type", sos_type)
        results = q.limit(limit).execute()
        if not results or results.data is None:
            raise Exception("Query failed")
        return JSONResponse(content={
            "status": "success",
            "alerts": results.data
        })
    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "message": f"Failed to list SOS alerts: {str(e)}"
        }, status_code=500)

# --- API: Resolve/mark alert as handled ---
@router.post("/resolve_sos/{alert_id}")
async def resolve_sos(alert_id: str):
    """
    Mark an SOS alert as resolved/handled.
    For use by field teams, control room, or dashboard ops.
    """
    try:
        now = time.time()
        update = supabase.table("sos_alerts").update({"status": "resolved", "resolved_at": now}).eq("alert_id", alert_id).execute()
        if not update or update.data is None or len(update.data) == 0:
            return JSONResponse(content={"status": "error", "message": "Alert not found or update failed"}, status_code=404)
        return JSONResponse(content={
            "status": "success",
            "message": "SOS alert marked as resolved.",
            "alert": update.data[0]
        })
    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "message": f"Failed to resolve SOS: {str(e)}"
        }, status_code=500)

# --- End of app/api/v1/sos.py ---