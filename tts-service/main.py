from fastapi import FastAPI, HTTPException, Response, Form
from fastapi.responses import HTMLResponse
import uvicorn
import logging
from pydantic import BaseModel

from tts_processor import create_tts_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TTSService")

tts_processor = create_tts_processor()
app = FastAPI(title="TTS")

class TtsReq(BaseModel):
    text: str
    voice: str = "af_heart"

@app.post("/speak")
async def tts_post(req: TtsReq):
    if not tts_processor:
        raise HTTPException(status_code=503, detail="Service not ready")

    result = tts_processor.text_to_speech(req.text, req.voice)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return Response(
        content=result["audio_data"],
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=speech.wav"}
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "tts-service"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=False)

