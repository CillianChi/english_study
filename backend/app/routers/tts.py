from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import tts_service
from ..db import get_db

router = APIRouter(tags=["tts"])


@router.get("/tts/{word}")
async def get_tts(word: str, db: Session = Depends(get_db)):
    word = word.strip().lower()

    # Whitelist against the word list -- this endpoint has no auth, so without
    # this check it'd be an open free-text TTS proxy for anyone who finds the URL.
    exists = db.execute(
        text("SELECT 1 FROM words WHERE word = :w"), {"w": word}
    ).first()
    if exists is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "word not found")

    path = await tts_service.get_or_create_audio(word)
    return FileResponse(path, media_type="audio/mpeg")
