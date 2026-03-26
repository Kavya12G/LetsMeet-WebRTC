from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/protected", tags=["Protected"])

@router.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email
    }

@router.get("/ice-config")
def get_ice_config(current_user: User = Depends(get_current_user)):
    return {
        "iceServers": [
            {"urls": "stun:stun.l.google.com:19302"},
            {
                "urls": settings.TURN_URL,
                "username": settings.TURN_USERNAME,
                "credential": settings.TURN_CREDENTIAL
            }
        ]
    }