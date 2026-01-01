
import logging
import soundfile as sf
import io
import numpy as np
from kokoro import KPipeline

class TTSProcessor:
    def __init__(self):
        self.logger = logging.getLogger("TTSProcessor")
        self.pipeline = None
        self._load_model()
    
    def _load_model(self):
        try:
            self.logger.info("Loading Kokoro model")
            self.pipeline = KPipeline(lang_code='a')
            self.logger.info("Kokoro model loaded")
        except Exception as e:
            self.logger.error(f"failed to load Kokoro model: {e}")
            raise
    
    def text_to_speech(self, text: str, voice: str = "af_heart") -> dict:
        if not text.strip():
            return {"success": False, "error": "Empty text"}
        
        try:
            text_length = len(text)
            self.logger.info(f"Processing text: {text_length} characters")
            
            if text_length > 1000:
                self.logger.info("will process in chunks because text is long")# Up to 500 characters per text-to-audio generation.
                
            generator = self.pipeline(text, voice=voice)
            
            # collecting all audio chunks
            audio_chunks = []
            for i, (gs, ps, audio) in enumerate(generator):
                self.logger.debug(f"Processing chunk {i}: {len(audio)} samples")
                audio_chunks.append(audio)
            
            if not audio_chunks:
                return {"success": False, "error": "No audio generated"}
            
            # combine all chunks together
            final_audio = np.concatenate(audio_chunks)

            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, final_audio, 24000, format='WAV')
            audio_bytes = audio_buffer.getvalue()
            
            self.logger.info(f"Generated {len(audio_bytes)} bytes from {len(audio_chunks)} chunks")
            
            return {
                "success": True, 
                "audio_data": audio_bytes,
                "chunks_processed": len(audio_chunks),
                "text_length": text_length
            }
            
        except Exception as e:
            self.logger.error(f"TTS generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def is_ready(self) -> bool:
        return self.pipeline is not None

def create_tts_processor():
    return TTSProcessor()