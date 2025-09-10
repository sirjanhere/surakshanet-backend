from app.api.v1 import crowd, sos, anomaly, navigation
# Do NOT import face

app = FastAPI()

app.include_router(crowd.router, prefix="/api/v1/crowd")
# app.include_router(face.router, prefix="/api/v1/face")  # Commented temporarily
app.include_router(sos.router, prefix="/api/v1/sos")
app.include_router(anomaly.router, prefix="/api/v1/anomaly")
app.include_router(navigation.router, prefix="/api/v1/navigation")