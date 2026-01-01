import gradio as gr
import requests
import uuid
import os
import base64

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000/process_audio/")

ALLOWED_FORMATS = ["wav", "mp3", "m4a", "flac"]
def process_audio_ui(audio_file):
    if not audio_file:
        return "No audio provided", None, None, None, None

    file_ext = audio_file.split('.')[-1].lower()
    if file_ext not in ALLOWED_FORMATS:
        return f"Unsupported format. Use: {ALLOWED_FORMATS}", None, None, None, None

    try:
        with open(audio_file, "rb") as f:
            files = {"file": (str(uuid.uuid4()) + f".{file_ext}", f, f"audio/{file_ext}")}
            response = requests.post(ORCHESTRATOR_URL, files=files, timeout=60)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        return f"Error contacting orchestrator: {e}", None, None, None, None

    transcription = data.get("transcription", "")
    llm_output = data.get("llm_output", {})
    validation_output = data.get("validation_output", {})
    tts_audio_base64 = data.get("tts_audio_base64")
    error = data.get("error", None)

    # Decode base64 TTS audio and save temporarily
    tts_audio_path = None
    if tts_audio_base64:
        audio_bytes = base64.b64decode(tts_audio_base64)
        tmp_filename = f"/tmp/{uuid.uuid4()}.m4a"  # assuming wav, adjust if needed
        with open(tmp_filename, "wb") as f:
            f.write(audio_bytes)
        tts_audio_path = tmp_filename

    return transcription, llm_output, validation_output, tts_audio_path, error
# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("# Robot Voice Assistant UI")
    gr.Markdown("Record audio to control SHATO.")

    with gr.Row():
        with gr.Column():
            audio_in = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Input Audio")
            submit_btn = gr.Button("Send to Orchestrator")

        with gr.Column():
            transcription = gr.Textbox(label="STT Transcription")
            llm_output = gr.JSON(label="LLM Output (Full JSON)")
            validation_output = gr.JSON(label="Validation Result")
            tts_audio = gr.Audio(label="TTS Response (Robot Reply)", type="filepath")
            error_box = gr.Textbox(label="Errors", interactive=False)

    submit_btn.click(
        process_audio_ui,
        inputs=audio_in,
        outputs=[transcription, llm_output, validation_output, tts_audio, error_box],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)