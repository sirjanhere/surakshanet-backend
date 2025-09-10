"""
Crowd Detection API – Real-time and Accurate

- Uses YOLOv8 to detect and count people in uploaded images.
- Returns the exact number of people detected.
- Requires: pip install ultralytics opencv-python-headless pillow
- Download YOLOv8s model automatically if not present.
"""

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from PIL import Image
import numpy as np
import io

# Import YOLO; make sure ultralytics is installed: pip install ultralytics
from ultralytics import YOLO

router = APIRouter()

# Load YOLOv8 model (first call downloads weights if not present)
yolo_model = YOLO('yolov8s.pt')  # You can use yolov8n.pt for faster/lighter model

@router.post("/detect")
async def detect_crowd(file: UploadFile = File(...)):
    """
    Accepts an image upload, runs YOLOv8, and returns the exact person count.
    """
    contents = await file.read()
    try:
        # Open image and convert to numpy array for YOLO
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        img_np = np.array(image)

        # Run inference; results has bounding boxes and class info
        results = yolo_model(img_np)

        # YOLOv8: class 0 is "person" in COCO dataset
        people_count = 0
        try:
            # For new ultralytics, results[0].boxes.cls contains the classes
            for c in results[0].boxes.cls:
                if int(c) == 0:  # class 0 == person
                    people_count += 1
        except Exception:
            # Fallback for older versions
            people_count = sum(1 for c in results[0].boxes.cls if int(c) == 0)

        return JSONResponse(content={
            "status": "success",
            "message": "Crowd detected successfully.",
            "count": people_count
        })
    except Exception as e:
        # If the uploaded file is not a valid image, or error during model run
        return JSONResponse(content={
            "status": "error",
            "message": f"Error during detection: {str(e)}"
        }, status_code=400)