from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from stt_processor import create_stt_processor

app = FastAPI(title="STT Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

stt_processor = create_stt_processor()

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    allowed_formats = ["wav", "mp3", "m4a", "flac"]
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in allowed_formats:
        raise HTTPException(status_code=400, detail=f"Unsupported format. Use: {allowed_formats}")
    
    audio_data = await file.read()
    
    # if len(audio_data) > 10 * 1024 * 1024:
    #     raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    
    result = stt_processor.transcribe_audio(audio_data, file_ext)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return {
        "text": result["transcribed_text"],
        "success": result["success"]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "stt-service"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=False)