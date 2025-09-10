"""
Face Recognition API – Real-time for Flagging Missing Persons

- Detects and recognizes faces in a real-time uploaded image.
- Compares detected faces against a database of missing persons ("known faces").
- Returns detected faces and flags if a missing person is found.
- Designed for large events (like Mahakumbh): only missing persons' data is stored, not the entire crowd.
- No dummy code; works in real time.
- Requires: pip install face_recognition opencv-python-headless pillow numpy

How to add missing persons:
- Save their clear face photos in a folder (e.g., "app/known_faces/").
- File names should be the person's name or unique ID (e.g., "ram_kumar.jpg").
"""

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from PIL import Image
import numpy as np
import io
import os
import face_recognition

router = APIRouter()

# ==== CONFIGURATION ====
# Folder containing face images of all missing persons
KNOWN_FACES_DIR = os.path.join(os.path.dirname(__file__), "..", "known_faces")

# ==== LOAD KNOWN FACE ENCODINGS (runs once at startup) ====
known_face_encodings = []
known_face_names = []

if os.path.exists(KNOWN_FACES_DIR):
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            image_path = os.path.join(KNOWN_FACES_DIR, filename)
            try:
                img = face_recognition.load_image_file(image_path)
                encodings = face_recognition.face_encodings(img)
                if encodings:
                    known_face_encodings.append(encodings[0])
                    # Use filename (without extension) as the person's name/ID
                    known_face_names.append(os.path.splitext(filename)[0])
            except Exception as e:
                # If an image is not valid for encoding, skip it
                print(f"Warning: Could not process {filename}: {e}")

@router.post("/recognize")
async def recognize_face(file: UploadFile = File(...)):
    """
    Accepts an image upload, detects and identifies faces,
    flags if a missing person is detected.
    """
    contents = await file.read()
    try:
        # Convert the uploaded file to a numpy array for face_recognition
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        image_np = np.array(image)

        # Detect all face locations and encodings in the image
        face_locations = face_recognition.face_locations(image_np)
        face_encodings = face_recognition.face_encodings(image_np, face_locations)

        faces_info = []
        flagged_missing = []

        for i, (face_encoding, face_location) in enumerate(zip(face_encodings, face_locations)):
            name = "Unknown"
            flagged = False

            # Compare this face to all known missing persons
            if known_face_encodings:
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.5)
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                if True in matches:
                    # Get the best match
                    best_match_index = np.argmin(face_distances)
                    name = known_face_names[best_match_index]
                    flagged = True
                    flagged_missing.append({
                        "face_id": i + 1,
                        "name": name,
                        "location": {
                            "top": face_location[0],
                            "right": face_location[1],
                            "bottom": face_location[2],
                            "left": face_location[3]
                        }
                    })

            faces_info.append({
                "face_id": i + 1,
                "location": {
                    "top": face_location[0],
                    "right": face_location[1],
                    "bottom": face_location[2],
                    "left": face_location[3]
                },
                "name": name,
                "is_missing_person": flagged
            })

        return JSONResponse(content={
            "status": "success",
            "num_faces": len(faces_info),
            "faces": faces_info,
            "flagged_missing_persons": flagged_missing
        })
    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "message": f"Error during face recognition: {str(e)}"
        }, status_code=400)