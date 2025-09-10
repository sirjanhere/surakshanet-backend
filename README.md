# SurakshaNet

## Public Code Repository Link
- **GitHub:** [https://github.com/sirjanhere/surakshanet-backend](https://github.com/sirjanhere/surakshanet-backend) 
[https://github.com/sirjanhere/surakshanet-frontend](https://github.com/sirjanhere/surakshanet-frontend) 

---

## One-Page Summary of Prototype

**SurakshaNet Backend** is a modular, production-grade backend system built in Python (FastAPI) for real-time safety, crowd, and event management, especially for large-scale events like Simhastha 2028. It integrates with Supabase/Postgres for fast, consistent data, delivering APIs for crowd/face/anomaly detection, navigation, SOS alerts, and complete admin control. The system enables authorities to manage emergencies, analyze crowds, respond to SOS, and maintain safety with actionable intelligence and full transparency.

---

## Key Features and Functionalities

- **User & Event Management:** Admin dashboard for user stats, search, and full audit logs.
- **Real-time SOS Alerts:** Pilgrims/staff can trigger SOS; supports photo upload, status tracking, and field team resolution.
- **Crowd Detection:** Upload images to count people in real-time with YOLOv8.
- **Face Recognition:** Match faces in images to missing persons (privacy-first, no crowd surveillance).
- **Anomaly Detection:** Identify abnormal spikes or drops in crowd/sensor data using AI models.
- **Hybrid Navigation:** Safe/fast routing using Google Maps or OpenStreetMap, with risk zone avoidance.
- **Admin Tools:** Broadcast alerts, force sync, clear cache, and monitor system health.
- **Supabase/Postgres Integration:** Real-time database and storage, scalable and production ready.

---

---

## The Core Problem Being Addressed

**SurakshaNet Backend** addresses the challenge of managing safety and logistics at mass gatherings, where crowd surges, missing persons, and emergencies are common. It enables:
- Real-time detection and response to dangerous crowd conditions.
- Rapid SOS alerting and resolution for emergencies.
- Smart, risk-aware navigation for attendees and responders.
- Full admin oversight, analytics, and transparency.

---

## Clear Overview of Prototype/Idea

- **Architecture:** Organized in modular FastAPI endpoints (each core function in its own file under `app/api/v1/`).
- **Deployment:** Works locally or in the cloud; easy configuration using `.env` for secrets/keys.
- **Accessibility:** Fully open-source on GitHub, no login barriers.
- **API Design:** Each API is stateless, production-ready, and privacy-centric.

---

## Detailed Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/sirjanhere/surakshanet-backend.git
cd surakshanet-backend
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key dependencies:**
- fastapi, uvicorn, pydantic (API)
- supabase, asyncpg (database)
- scikit-learn, numpy (anomaly detection)
- ultralytics, opencv-python-headless, pillow (crowd detection)
- face_recognition, pillow, numpy (face recognition)
- geopy, networkx, osmnx, requests (navigation)

If you encounter errors about system libraries (e.g., `dlib` for face recognition), install OS-level prerequisites. For Ubuntu:
```bash
sudo apt-get update
sudo apt-get install build-essential cmake libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory (or use actual environment variables):

```
SUPABASE_URL=https://<your_supabase_project>.supabase.co
SUPABASE_KEY=<your_supabase_service_key>
SUPABASE_DB_URL=postgresql://<user>:<pass>@<host>:<port>/<db>
SUPABASE_BUCKET=sos-photos
GOOGLE_MAPS_API_KEY=<your_google_maps_api_key>
```

- **SUPABASE_URL & SUPABASE_KEY:** Required for DB/storage.
- **SUPABASE_DB_URL:** For direct health checks.
- **SUPABASE_BUCKET:** For storing SOS photos (default is `sos-photos`).
- **GOOGLE_MAPS_API_KEY:** Needed for navigation API.

### 5. Prepare Folders

- For **face recognition**, add clear images of missing persons to `app/known_faces/`, named as `<person_name>.jpg`.

### 6. Run the Application

```bash
uvicorn app.main:app --reload
```

- By default, runs at [http://localhost:8000](http://localhost:8000)
- Interactive API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 7. Test APIs

- Use Swagger docs (`/docs`) or Postman for testing endpoints.
- For image endpoints, upload files as `multipart/form-data`.

---


## API Documentation

### API Endpoints in `app/api/v1`

#### `admin.py` – Admin Control & Analytics

- **GET `/admin/stats`**  
  Returns real-time dashboard stats: user count, SOS status, event counts, and system health for all modules (SOS, crowd, face, navigation, anomaly, DB, Supabase).

- **GET `/admin/users`**  
  Lists or searches users in the system (by name, email, or phone). Used in admin control panel.

- **GET `/admin/logs`**  
  Fetches recent event logs for audit trail and admin/system actions.

- **POST `/admin/broadcast`**  
  Broadcasts an admin message to all connected dashboards/apps. Messages are logged and can be extended to push to real-time clients.

- **POST `/admin/force_sync`**  
  Triggers a production-safe "force sync" event (can be extended to launch jobs/tasks).

- **POST `/admin/clear_cache`**  
  Clears system cache (stub for integration with Redis or other cache backends).

#### `anomaly.py` – Real-time Anomaly Detection

- **POST `/detect`**  
  Detects anomalies in time-series data (e.g., crowd counts, sensor data) using IsolationForest.  
  - Input: JSON with `"data": [values]` (at least 5).  
  - Output: Whether the latest value is anomalous, indices of anomalies, anomaly scores, and a dashboard message.  
  - Used for flagging crowd surges, suspicious activity, or abnormal movement.

#### `crowd.py` – Crowd Detection

- **POST `/detect`**  
  Accepts an uploaded image and uses YOLOv8 to detect/count people.  
  - Input: Image file (`multipart/form-data`).  
  - Output: Exact number of people detected.  
  - Used for real-time crowd estimation from cameras.

#### `face.py` – Face Recognition (Missing Persons)

- **POST `/recognize`**  
  Accepts an uploaded image, detects all faces, and compares them against a database of missing persons (in `known_faces/`).  
  - Input: Image file.  
  - Output: Detected faces, locations, names (if matched), and flags for missing persons.
  - No crowd storage; only missing persons' data is stored for privacy.

#### `navigation.py` – Hybrid Navigation API

- **POST `/route`**  
  Computes the safest or fastest route between two points using either Google Maps API or OpenStreetMap (OSMnx/NetworkX), optionally avoiding risk zones.  
  - Input: Source/destination as coordinates or place names, optional risk zones, routing mode.
  - Output: Route coordinates, distance, step-by-step instructions, and advisories.

#### `sos.py` – Real-time SOS Alerts

- **POST `/trigger_sos`**  
  Triggers a new SOS alert (medical/security/lost/other) with user/location/details and optional photo.  
  - Input: Form data (supports mobile/kiosk).
  - Stores alert in Supabase and publishes for dashboards/field teams.

- **GET `/alerts`**  
  Lists all or only active SOS alerts, filterable by status/type. Supports dashboard live updates.

- **POST `/resolve_sos/{alert_id}`**  
  Marks an SOS alert as resolved/handled. Used by field teams and ops.

---

## Development Guidelines

- Code: PEP8, modular.
- Tests: Add unit/integration tests for new features.
- Commits: Descriptive messages.
- Issues/PRs: Use GitHub for collaboration.

---

