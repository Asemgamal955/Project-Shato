import os
import tempfile
import logging
from typing import Dict, Optional, Union
from pathlib import Path
import whisper
import torch

class STTProcessor:

    def __init__(self, model_name: str = "small"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.logger = self._setup_logger()
        
        self._load_model()
    
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("STTProcessor")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_model(self) -> None:
        try:
            self.logger.info(f"loading model '{self.model_name}'")
            self.model = whisper.load_model(self.model_name, device=self.device)
            self.logger.info("model loaded successfully")
        except Exception as e:
            self.logger.error(f"couldn't load model: {str(e)}")
            raise RuntimeError(f"couldn't load model: {str(e)}")
    
    def transcribe_audio(self, audio_data: bytes, audio_format: str = "wav") -> Dict[str, Union[str, float]]:
        if not self.model:
            raise RuntimeError("model not loaded")
        
        try:
            # temporary file for audio data
            with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            try:
                self.logger.info(f"Transcribing audio file: {temp_path}")
                result = self.model.transcribe(
                    temp_path,
                    language="en",
                    task="transcribe",  # transcribe
                    fp16=torch.cuda.is_available()
                )
                
                transcribed_text = result["text"].strip()
                
                self.logger.info(f"Transcription successful: '{transcribed_text[:50]}...'")
                
                return {
                    "transcribed_text": transcribed_text,
                    "model_used": self.model_name,
                    "device_used": self.device,
                    "success": True
                }
                
            finally:
                # remove temporary file
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Transcription failed: {str(e)}")
            return {
                "transcribed_text": "",
                "error": str(e),
                "model_used": self.model_name,
                "device_used": self.device,
                "success": False
            }
        
def create_stt_processor(model_name: str = "small"):
    return STTProcessor(model_name=model_name)

