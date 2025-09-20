# helpers/serialize.py  -- convert odmantic models to API-safe dicts
from datetime import datetime
from typing import Any, Dict

def oid_to_str(obj_id):
    # Odmantic model.id is usually BSON ObjectId -> convert to str
    return str(obj_id) if obj_id is not None else None

def usermodel_to_public_dict(user):
    # user: Odmantic UserModel instance
    return {
        "_id": oid_to_str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "pseudonym": user.pseudonym,
        "is_mentor": user.is_mentor,
        "preferences": user.preferences,
        "created_at": user.created_at.isoformat() if isinstance(user.created_at, datetime) else user.created_at
    }

def dreammodel_to_dict(d):
    return {
        "_id": oid_to_str(d.id),
        "user_id": d.user_id,
        "timestamp": d.timestamp.isoformat() if d.timestamp else None,
        "text_content": d.text_content,
        "audio_url": d.audio_url,
        "analysis": d.analysis,
        "status": d.status,
        "created_at": d.created_at.isoformat() if d.created_at else None
    }
