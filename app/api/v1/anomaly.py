"""
SurakshaNet – Real-time Anomaly Detection API
---------------------------------------------

Purpose:
- Detects crowd or behavioral anomalies in real-time from event camera feeds, sensors, or crowd counters.
- Used to flag sudden crowd surges (stampede risk), abnormal movement, or suspicious activity at Simhastha 2028.
- Integrates with AI-powered CCTV, drones, or IoT sensors in the SurakshaNet platform.

Approach:
- Uses IsolationForest (scikit-learn) for unsupervised anomaly detection on time-series data.
- Data may include crowd counts (from YOLOv8/CSRNet), movement densities, or sensor readings.
- Flags the latest value as "anomalous" if it deviates sharply from recent trends.
- Designed for online use: quick, robust, and interpretable for authorities.

Security & Ethics:
- No personal or facial data is processed or stored here.
- Only numeric time series (e.g., [count1, count2, ...]) are analyzed.

Dependencies:
- pip install fastapi uvicorn scikit-learn numpy pydantic

POST Example:
{
  "data": [120, 125, 123, 400, 124, 126]
}
If 400 is a spike, it will be flagged as anomaly.

Returns:
- is_latest_anomaly (true/false)
- indices of all anomalies
- anomaly scores for transparency
- clear message for dashboard display
"""

from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from sklearn.ensemble import IsolationForest
import numpy as np

router = APIRouter()

class AnomalyRequest(BaseModel):
    data: list  # Recent time-series data (e.g., crowd counts, densities, sensor readings)

@router.post("/detect")
async def detect_anomaly(request: AnomalyRequest):
    """
    Detects crowd/sensor anomalies in real time using Isolation Forest.
    Flags sudden surges, drops, or suspicious behaviors for operator response.
    """
    # Validate input
    if not isinstance(request.data, list) or len(request.data) < 5:
        return JSONResponse(content={
            "status": "error",
            "message": "At least 5 numeric values required for reliable anomaly detection."
        }, status_code=400)

    try:
        # Convert to numpy and reshape for scikit-learn
        arr = np.array(request.data).reshape(-1, 1)

        # Configure IsolationForest: contamination can be tuned per use-case
        model = IsolationForest(contamination=0.12, random_state=28, n_estimators=100)
        model.fit(arr)

        # Predict: -1 = anomaly, 1 = normal
        preds = model.predict(arr)
        anomaly_indices = [i for i, p in enumerate(preds) if p == -1]
        scores = model.decision_function(arr)  # Lower = more abnormal

        # Is latest value (most recent) anomalous?
        is_latest_anomaly = preds[-1] == -1

        # For dashboard: show what the anomaly was if flagged
        latest_value = request.data[-1]

        return JSONResponse(content={
            "status": "success",
            "is_latest_anomaly": bool(is_latest_anomaly),
            "anomaly_indices": anomaly_indices,
            "anomaly_scores": [float(s) for s in scores],
            "latest_value": latest_value,
            "message": (
                f"ALERT: Abnormal surge/drop detected (value={latest_value})! "
                "Please investigate immediately."
                if is_latest_anomaly else
                "No anomaly detected in the latest reading."
            )
        })
    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "message": f"Anomaly detection failed: {str(e)}"
        }, status_code=500)