"""
Enhanced orchestrator with validator service integration and TTS support.
Replace your orchestrator/orchestrator.py with this version.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import requests
import os
import traceback
import io
import base64

app = FastAPI(title="SHATO Orchestrator")

STT_URL = "http://stt-service:8003/transcribe"
LLM_URL = os.getenv("LLM_URL", "http://llm-service:9000")
VALIDATOR_URL = os.getenv("VALIDATOR_URL", "http://robot-validator:8001")
TTS_URL = os.getenv("TTS_URL", "http://tts-service:8004")

def call_llm(transcription_text: str):
    if not transcription_text:
        print("[DEBUG] Empty transcription provided to LLM")
        return {"llm_output": None, "model_raw": None, "retrieved": None, "error": "Empty transcription"}

    try:
        payload = {"message": transcription_text}
        llm_endpoint = f"{LLM_URL}/chat"
        
        print(f"[DEBUG] Sending to LLM-service at {llm_endpoint}")
        print(f"[DEBUG] LLM payload: {payload}")
        
        r = requests.post(llm_endpoint, json=payload, timeout=60)
        
        print(f"[DEBUG] LLM response status: {r.status_code}")
        print(f"[DEBUG] LLM response headers: {dict(r.headers)}")
        
        if r.status_code != 200:
            error_detail = f"LLM service returned {r.status_code}"
            try:
                error_body = r.text
                print(f"[ERROR] LLM error body: {error_body}")
                error_detail += f": {error_body}"
            except:
                pass
            return {"llm_output": None, "model_raw": None, "retrieved": None, "error": error_detail}
        
        r.raise_for_status()
        data = r.json()
        print(f"[DEBUG] LLM response data: {data}")
        
        return {
            "llm_output": data.get("llm_output"),
            "model_raw": data.get("model_raw"),
            "retrieved": data.get("retrieved"),
            "error": data.get("error")
        }
        
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Cannot connect to LLM service at {LLM_URL}: {e}"
        print(f"[ERROR] {error_msg}")
        return {"llm_output": None, "model_raw": None, "retrieved": None, "error": error_msg}
        
    except requests.exceptions.Timeout as e:
        error_msg = f"LLM request timed out: {e}"
        print(f"[ERROR] {error_msg}")
        return {"llm_output": None, "model_raw": None, "retrieved": None, "error": error_msg}
        
    except requests.exceptions.RequestException as e:
        error_msg = f"LLM request failed: {e}"
        print(f"[ERROR] {error_msg}")
        return {"llm_output": None, "model_raw": None, "retrieved": None, "error": error_msg}
        
    except Exception as e:
        error_msg = f"Unexpected LLM error: {e}"
        print(f"[ERROR] {error_msg}")
        traceback.print_exc()
        return {"llm_output": None, "model_raw": None, "retrieved": None, "error": error_msg}

def call_validator(llm_output):
    """Call the validator service to validate and execute commands"""
    if not llm_output or not isinstance(llm_output, dict):
        print("[DEBUG] No valid LLM output to validate")
        return {"validation_output": None, "error": "No LLM output to validate"}
    
    command = llm_output.get("command")
    command_params = llm_output.get("command_params")
    
    # Skip validation if no command or command is null
    if not command or command == "null":
        print("[DEBUG] No command to validate - skipping validator")
        return {"validation_output": {"status": "skipped", "reason": "No command to validate"}, "error": None}
    
    try:
        validator_endpoint = f"{VALIDATOR_URL}/execute_command"
        payload = {
            "command": command,
            "command_params": command_params or {}
        }
        
        print(f"[DEBUG] Sending to Validator at {validator_endpoint}")
        print(f"[DEBUG] Validator payload: {payload}")
        
        r = requests.post(validator_endpoint, json=payload, timeout=30)
        
        print(f"[DEBUG] Validator response status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print(f"[DEBUG] Validator response data: {data}")
            return {"validation_output": data, "error": None}
        else:
            # Get error details
            try:
                error_data = r.json()
                error_detail = error_data.get("detail", f"Validator returned {r.status_code}")
            except:
                error_detail = f"Validator returned {r.status_code}: {r.text}"
            
            print(f"[ERROR] Validator error: {error_detail}")
            return {
                "validation_output": {
                    "status": "error", 
                    "error": error_detail
                }, 
                "error": f"Validation failed: {error_detail}"
            }
        
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Cannot connect to Validator service at {VALIDATOR_URL}: {e}"
        print(f"[ERROR] {error_msg}")
        return {
            "validation_output": {"status": "error", "error": "Validator service unavailable"}, 
            "error": error_msg
        }
        
    except requests.exceptions.Timeout as e:
        error_msg = f"Validator request timed out: {e}"
        print(f"[ERROR] {error_msg}")
        return {
            "validation_output": {"status": "error", "error": "Validator timeout"}, 
            "error": error_msg
        }
        
    except Exception as e:
        error_msg = f"Unexpected validator error: {e}"
        print(f"[ERROR] {error_msg}")
        traceback.print_exc()
        return {
            "validation_output": {"status": "error", "error": str(e)}, 
            "error": error_msg
        }

def call_tts(text: str, voice: str = "af_heart", response_type: str = "chat"):
    """Call the TTS service to convert text to speech with voice selection based on response type"""
    if not text or not text.strip():
        print("[DEBUG] No text provided for TTS")
        return {"tts_audio_data": None, "error": "No text to convert to speech"}
    
    # Select voice based on response type
    voice_mapping = {
        "success": "af_heart",      # Friendly voice for successful commands
        "error": "af_bella",        # Different voice for errors (more serious tone)
        "chat": "af_heart"          # Default friendly voice for chat responses
    }
    
    selected_voice = voice_mapping.get(response_type, voice)
    
    try:
        tts_endpoint = f"{TTS_URL}/speak"
        payload = {
            "text": text,
            "voice": selected_voice
        }
        
        print(f"[DEBUG] Sending to TTS service at {tts_endpoint}")
        print(f"[DEBUG] TTS payload: {payload} (response_type: {response_type})")
        
        r = requests.post(tts_endpoint, json=payload, timeout=30)
        
        print(f"[DEBUG] TTS response status: {r.status_code}")
        
        if r.status_code == 200:
            audio_data = r.content
            print(f"[DEBUG] TTS generated {len(audio_data)} bytes of audio")
            
            # Convert to base64 for JSON response
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return {
                "tts_audio_data": audio_base64,
                "audio_size": len(audio_data),
                "voice_used": selected_voice,
                "response_type": response_type,
                "error": None
            }
        else:
            # Get error details
            try:
                error_data = r.json()
                error_detail = error_data.get("detail", f"TTS service returned {r.status_code}")
            except:
                error_detail = f"TTS service returned {r.status_code}: {r.text}"
            
            print(f"[ERROR] TTS error: {error_detail}")
            return {
                "tts_audio_data": None,
                "error": f"TTS generation failed: {error_detail}"
            }
        
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Cannot connect to TTS service at {TTS_URL}: {e}"
        print(f"[ERROR] {error_msg}")
        return {
            "tts_audio_data": None,
            "error": error_msg
        }
        
    except requests.exceptions.Timeout as e:
        error_msg = f"TTS request timed out: {e}"
        print(f"[ERROR] {error_msg}")
        return {
            "tts_audio_data": None,
            "error": error_msg
        }
        
    except Exception as e:
        error_msg = f"Unexpected TTS error: {e}"
        print(f"[ERROR] {error_msg}")
        traceback.print_exc()
        return {
            "tts_audio_data": None,
            "error": error_msg
        }

def get_response_text_and_type(llm_output, validation_output):
    """Extract the most appropriate text to convert to speech and determine response type"""
    
    # Determine response type and text based on validation status
    if validation_output and isinstance(validation_output, dict):
        validation_status = validation_output.get("status", "").lower()
        
        if validation_status == "success":
            # Command executed successfully - use LLM response
            response_text = None
            if llm_output and isinstance(llm_output, dict):
                response_text = llm_output.get("response")
            
            if not response_text:
                # Fallback success message
                command_name = ""
                if validation_output.get("data", {}).get("command"):
                    command_name = f" '{validation_output['data']['command']}'"
                response_text = f"Command{command_name} executed successfully."
            
            return response_text, "success"
            
        elif validation_status == "error":
            # Command failed - create error message
            error_detail = validation_output.get("error", "Unknown error")
            response_text = f"Command failed: {error_detail}"
            return response_text, "error"
            
        elif validation_status == "skipped":
            # No command to execute - this is a chat response
            if llm_output and isinstance(llm_output, dict):
                response_text = llm_output.get("response")
                if response_text:
                    return response_text, "chat"
    
    # Fallback for chat responses when no validation occurred
    if llm_output and isinstance(llm_output, dict):
        response_text = llm_output.get("response")
        if response_text:
            return response_text, "chat"
        if llm_output.get("message"):
            return llm_output["message"], "chat"
        if llm_output.get("text"):
            return llm_output["text"], "chat"
    
    # Final fallback
    return "I processed your request but have no specific response to provide.", "chat"

@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No audio provided")

    print(f"[DEBUG] Processing audio file: {file.filename}")
    
    try:
        audio_bytes = await file.read()
        print(f"[DEBUG] Audio file size: {len(audio_bytes)} bytes")
        
        files = {"file": (file.filename, audio_bytes, "audio/wav")}

        # Step 1: Call STT
        try:
            print(f"[DEBUG] Sending audio to STT-service: {file.filename}")
            stt_response = requests.post(STT_URL, files=files, timeout=60)
            
            print(f"[DEBUG] STT response status: {stt_response.status_code}")
            
            if stt_response.status_code != 200:
                error_detail = f"STT service returned {stt_response.status_code}"
                try:
                    error_body = stt_response.text
                    print(f"[ERROR] STT error body: {error_body}")
                    error_detail += f": {error_body}"
                except:
                    pass
                raise HTTPException(status_code=500, detail=error_detail)
            
            stt_response.raise_for_status()
            stt_json = stt_response.json()
            print(f"[DEBUG] STT response: {stt_json}")
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Cannot connect to STT service: {e}"
            print(f"[ERROR] {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"STT request failed: {e}"
            print(f"[ERROR] {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
            
        except Exception as e:
            error_msg = f"STT processing failed: {e}"
            print(f"[ERROR] {error_msg}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=error_msg)

        # Extract transcription
        transcription = stt_json.get("text", "") or stt_json.get("transcribed_text", "")
        
        if not transcription:
            print("[WARNING] No transcription text found in STT response")
            transcription = ""

        print(f"[DEBUG] Transcription: '{transcription}'")

        # Step 2: Call LLM
        llm_result = call_llm(transcription)
        print(f"[DEBUG] LLM result: {llm_result}")
        
        # Step 3: Call Validator if we have a command
        llm_output = llm_result.get("llm_output")
        validator_result = call_validator(llm_output)
        print(f"[DEBUG] Validator result: {validator_result}")
        
        # Step 4: Generate TTS response
        validation_output = validator_result.get("validation_output")
        response_text, response_type = get_response_text_and_type(llm_output, validation_output)
        print(f"[DEBUG] Response text for TTS: '{response_text}' (type: {response_type})")
        
        tts_result = call_tts(response_text, response_type=response_type)
        print(f"[DEBUG] TTS result: {tts_result}")

        # Step 5: Combine errors
        combined_errors = []
        if llm_result.get("error"):
            combined_errors.append(f"LLM: {llm_result['error']}")
        if validator_result.get("error"):
            combined_errors.append(f"Validator: {validator_result['error']}")
        if tts_result.get("error"):
            combined_errors.append(f"TTS: {tts_result['error']}")
        
        final_error = "; ".join(combined_errors) if combined_errors else None

        # Step 6: Return combined response
        response = {
            "transcription": transcription,
            "llm_output": llm_output,
            "validation_output": validation_output,
            "tts_audio_base64": tts_result.get("tts_audio_data"),
            "tts_audio_size": tts_result.get("audio_size"),
            "tts_voice_used": tts_result.get("voice_used"),
            "response_text": response_text,
            "response_type": response_type,
            "error": final_error
        }
        
        print(f"[DEBUG] Final response: {response}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        error_msg = f"Orchestrator processing failed: {e}"
        print(f"[ERROR] {error_msg}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/tts/{text}")
async def direct_tts(text: str, voice: str = "af_heart"):
    """Direct TTS endpoint for testing"""
    tts_result = call_tts(text, voice)
    
    if tts_result.get("error"):
        raise HTTPException(status_code=500, detail=tts_result["error"])
    
    if not tts_result.get("tts_audio_data"):
        raise HTTPException(status_code=500, detail="No audio data generated")
    
    # Decode base64 audio data
    audio_data = base64.b64decode(tts_result["tts_audio_data"])
    
    return StreamingResponse(
        io.BytesIO(audio_data),
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=speech.wav"}
    )

@app.post("/tts")
async def tts_endpoint(text: str, voice: str = "af_heart"):
    """JSON TTS endpoint"""
    tts_result = call_tts(text, voice)
    
    if tts_result.get("error"):
        raise HTTPException(status_code=500, detail=tts_result["error"])
    
    return {
        "audio_base64": tts_result.get("tts_audio_data"),
        "audio_size": tts_result.get("audio_size"),
        "text": text,
        "voice": voice
    }

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "shato-orchestrator",
        "endpoints": {
            "stt_url": STT_URL,
            "llm_url": LLM_URL,
            "validator_url": VALIDATOR_URL,
            "tts_url": TTS_URL
        }
    }

@app.get("/health")
def health():
    # Test connectivity to all services
    services_status = {}
    
    # Test LLM
    try:
        r = requests.get(f"{LLM_URL}/health", timeout=5)
        services_status["llm"] = "healthy" if r.status_code == 200 else "unhealthy"
    except:
        services_status["llm"] = "unreachable"
    
    # Test STT
    try:
        r = requests.get(f"{STT_URL.replace('/transcribe', '/health')}", timeout=5)
        services_status["stt"] = "healthy" if r.status_code == 200 else "unhealthy"
    except:
        services_status["stt"] = "unreachable"
    
    # Test Validator
    try:
        r = requests.get(f"{VALIDATOR_URL}/health", timeout=5)
        services_status["validator"] = "healthy" if r.status_code == 200 else "unhealthy"
    except:
        services_status["validator"] = "unreachable"
    
    # Test TTS
    try:
        r = requests.get(f"{TTS_URL}/health", timeout=5)
        services_status["tts"] = "healthy" if r.status_code == 200 else "unhealthy"
    except:
        services_status["tts"] = "unreachable"
    
    overall_status = "healthy" if all(s == "healthy" for s in services_status.values()) else "degraded"
    
    return {
        "status": overall_status, 
        "service": "orchestrator",
        "dependencies": services_status
    }