"""
Enhanced LLM service with robust JSON parsing for LLM responses.
Replace your llm-service/app/api_rag.py with this version.
"""

import os, json, glob, requests
from typing import Dict, Any, List
from collections import Counter
import traceback
import re

import chromadb
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---------------- Config ----------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CHROMA_COLLECTION = "shato_examples"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 4
OLLAMA_MODEL = "gemma3:270m"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm-service:11434")

# Global variables for debugging
embed_model = None
collection = None
docs = []

def parse_llm_response(raw_output: str) -> dict:
    """
    Enhanced JSON parser that handles multiple LLM response formats:
    - Plain JSON
    - JSON wrapped in markdown code blocks
    - JSON with extra text
    - Malformed responses
    """
    if not raw_output or not raw_output.strip():
        return {
            "response": "No response received.",
            "command": None,
            "command_params": None
        }
    
    raw = raw_output.strip()
    print(f"[DEBUG] Raw output to parse: '{raw}'")
    
    # Strategy 1: Remove markdown code blocks
    if "```" in raw:
        # Extract content between code blocks
        code_block_pattern = r"```(?:json)?\s*(.*?)\s*```"
        matches = re.findall(code_block_pattern, raw, re.DOTALL | re.IGNORECASE)
        if matches:
            # Use the first/largest match
            raw = max(matches, key=len).strip()
            print(f"[DEBUG] Extracted from code blocks: '{raw}'")
    
    # Strategy 2: Find JSON object boundaries
    brace_count = 0
    start_idx = -1
    end_idx = -1
    
    for i, char in enumerate(raw):
        if char == '{':
            if start_idx == -1:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                end_idx = i
                break
    
    if start_idx != -1 and end_idx != -1:
        json_str = raw[start_idx:end_idx + 1]
        print(f"[DEBUG] Extracted JSON string: '{json_str}'")
        
        try:
            parsed = json.loads(json_str)
            
            # Validate the structure
            if isinstance(parsed, dict):
                # Ensure required fields exist
                result = {
                    "response": parsed.get("response", "Command received."),
                    "command": parsed.get("command"),
                    "command_params": parsed.get("command_params")
                }
                print(f"[DEBUG] Successfully parsed: {result}")
                return result
                
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON decode failed: {e}")
    
    # Strategy 3: Regex patterns for common formats
    patterns = [
        r'"command"\s*:\s*"([^"]*)".*?"command_params"\s*:\s*(\{[^}]*\})',
        r'command["\s]*[:=]["\s]*([^",\s}]+).*?params["\s]*[:=]["\s]*(\{[^}]*\})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
        if match:
            try:
                command = match.group(1).strip().strip('"')
                params_str = match.group(2)
                params = json.loads(params_str)
                
                result = {
                    "response": f"Executing {command} command.",
                    "command": command if command and command != "null" else None,
                    "command_params": params
                }
                print(f"[DEBUG] Regex extraction successful: {result}")
                return result
            except (json.JSONDecodeError, IndexError) as e:
                print(f"[DEBUG] Regex extraction failed: {e}")
                continue
    
    # Strategy 4: Extract key information with simple parsing
    command_keywords = ["move_to", "rotate", "start_patrol"]
    found_command = None
    
    for cmd in command_keywords:
        if cmd in raw.lower():
            found_command = cmd
            break
    
    # Extract coordinates if present
    coord_pattern = r'["\s]*x["\s]*[:=]["\s]*(\d+).*?["\s]*y["\s]*[:=]["\s]*(\d+)'
    coord_match = re.search(coord_pattern, raw, re.IGNORECASE)
    
    if found_command and coord_match:
        try:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            result = {
                "response": f"Moving to coordinates {x}, {y}.",
                "command": found_command,
                "command_params": {"x": x, "y": y}
            }
            print(f"[DEBUG] Keyword extraction successful: {result}")
            return result
        except ValueError as e:
            print(f"[DEBUG] Coordinate parsing failed: {e}")
    
    # Strategy 5: Fallback
    response_text = raw
    response_text = re.sub(r'[{}"\[\]]', '', response_text)
    response_text = re.sub(r'response\s*[:=]\s*', '', response_text, flags=re.IGNORECASE)
    response_text = re.sub(r'command\s*[:=]\s*\w+', '', response_text, flags=re.IGNORECASE)
    response_text = ' '.join(response_text.split())
    
    if not response_text:
        response_text = "I received your request but couldn't parse the response format."
    
    fallback_result = {
        "response": response_text[:200],
        "command": found_command,
        "command_params": None
    }
    
    print(f"[DEBUG] Using fallback result: {fallback_result}")
    return fallback_result

def load_samples(data_dir: str) -> List[Dict[str, Any]]:
    samples = []
    for path in glob.glob(os.path.join(data_dir, "*.json")):
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    samples.extend(data)
            except Exception as e:
                print(f"Error reading {path}: {e}")
    return samples

# Initialize components with better error handling
try:
    print("Loading data...")
    samples = load_samples(DATA_DIR)
    print("Loaded samples:", len(samples))
    
    if samples:
        print("Category counts:", Counter(s.get("category") for s in samples))
        valid_samples = [s for s in samples if isinstance(s.get("expected_output"), dict)]
        print("Valid-looking samples:", len(valid_samples))
    else:
        print("No samples loaded - creating empty collection")
        valid_samples = []

    print("Preparing embeddings and building Chroma index...")
    embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")

    client = chromadb.Client()
    if CHROMA_COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(CHROMA_COLLECTION)
    collection = client.create_collection(CHROMA_COLLECTION)

    if valid_samples:
        def doc_text(example):
            eo = example.get("expected_output", {})
            return json.dumps({
                "input": example.get("user_input"),
                "response": eo.get("response"),
                "command": eo.get("command"),
                "command_params": eo.get("command_params"),
            }, ensure_ascii=False)

        docs = [doc_text(s) for s in valid_samples]
        ids = [f"ex{i}" for i in range(len(docs))]
        metadatas = [{"category": s.get("category")} for s in valid_samples]
        embs = embed_model.encode(docs, show_progress_bar=True, convert_to_numpy=True)

        collection.add(documents=docs, ids=ids, metadatas=metadatas, embeddings=embs)
        print(f"Indexed {len(docs)} docs into Chroma collection '{CHROMA_COLLECTION}'")
    else:
        print("No valid samples to index - collection remains empty")

except Exception as e:
    print(f"CRITICAL ERROR during initialization: {e}")
    traceback.print_exc()

# ---------------- FastAPI ----------------
app = FastAPI(title="SHATO RAG API", version="2.2 (enhanced-parser)")

class QueryRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(req: QueryRequest):
    try:
        prompt = req.message.strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="Empty message")

        print(f"[DEBUG] Received message: '{prompt}'")

        # Check if components are initialized
        if embed_model is None or collection is None:
            print("[ERROR] Components not initialized properly")
            return {
                "input": prompt,
                "retrieved": [],
                "llm_output": {"response": "System initialization error", "command": None, "command_params": None},
                "model_raw": "Components not initialized",
                "error": "System not properly initialized"
            }

        # Retrieve top-k examples
        retrieved_docs = []
        try:
            if docs:
                q_emb = embed_model.encode([prompt], convert_to_numpy=True)[0]
                res = collection.query(query_embeddings=[q_emb], n_results=min(TOP_K, len(docs)), include=["documents"])
                retrieved_docs = res["documents"][0] if res and "documents" in res else []
                print(f"[DEBUG] Retrieved {len(retrieved_docs)} documents")
            else:
                print("[DEBUG] No documents available for retrieval")
        except Exception as e:
            print(f"[WARNING] Retrieval failed: {e}")
            retrieved_docs = []

        context = "\n\n".join(retrieved_docs)

        # Build system + context prompt with more explicit instructions
        system_msg = (
            """You are SHATO's command brain. You MUST respond with ONLY valid JSON.

CRITICAL: Your response must be EXACTLY this JSON format with no extra text:
{"response": "your message here", "command": "command_name_or_null", "command_params": {...} or null}

Valid commands: move_to, rotate, start_patrol
- For movement: {"command": "move_to", "command_params": {"x": number, "y": number}}
- For rotation: {"command": "rotate", "command_params": {"angle": number}}
- For patrol: {"command": "start_patrol", "command_params": null}
- For non-commands: {"command": null, "command_params": null}

DO NOT use markdown, code blocks, or any formatting. Output pure JSON only."""
        )

        full_prompt = f"{system_msg}\n\nContext examples:\n{context}\n\nUser: {prompt}\n\nAssistant:"
        print(f"[DEBUG] Full prompt length: {len(full_prompt)}")

        # Call Ollama
        try:
            ollama_endpoint = f"{OLLAMA_URL}/api/generate"
            payload = {
                "model": OLLAMA_MODEL, 
                "prompt": full_prompt, 
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Lower temperature for more consistent formatting
                    "top_p": 0.9
                }
            }
            
            print(f"[DEBUG] Calling Ollama at {ollama_endpoint}")
            
            r = requests.post(ollama_endpoint, json=payload, timeout=60)
            print(f"[DEBUG] Ollama response status: {r.status_code}")
            
            if r.status_code != 200:
                print(f"[ERROR] Ollama returned status {r.status_code}: {r.text}")
                raise Exception(f"Ollama returned status {r.status_code}")
                
            r.raise_for_status()
            data = r.json()
            raw_output = data.get("response", "").strip()
            print(f"[DEBUG] Raw Ollama output: '{raw_output}'")
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ollama request failed: {e}")
            return {
                "input": prompt,
                "retrieved": retrieved_docs,
                "llm_output": {"response": f"Failed to contact LLM: {str(e)}", "command": None, "command_params": None},
                "model_raw": f"Request error: {str(e)}",
                "error": f"Ollama request failed: {str(e)}"
            }

        # Use enhanced parsing
        parsed = parse_llm_response(raw_output)

        result = {
            "input": prompt,
            "retrieved": retrieved_docs,
            "llm_output": parsed,
            "model_raw": raw_output,
            "error": None
        }
        
        print(f"[DEBUG] Returning result: {result}")
        return result

    except Exception as e:
        print(f"[CRITICAL ERROR] Unhandled exception in chat endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/")
def root():
    return {
        "status": "ok", 
        "samples_indexed": len(docs), 
        "collection": CHROMA_COLLECTION,
        "ollama_url": OLLAMA_URL,
        "ollama_model": OLLAMA_MODEL,
        "components_ready": {
            "embed_model": embed_model is not None,
            "collection": collection is not None,
            "docs_count": len(docs)
        }
    }

@app.get("/health")
def health():
    # Test Ollama connectivity
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        ollama_status = "healthy" if r.status_code == 200 else "unhealthy"
    except:
        ollama_status = "unreachable"
    
    return {
        "status": "healthy" if ollama_status == "healthy" else "degraded",
        "service": "llm-rag-service", 
        "ollama_status": ollama_status,
        "components": {
            "embed_model": embed_model is not None,
            "collection": collection is not None,
            "docs_count": len(docs)
        }
    }

@app.get("/test-parser")
def test_parser():
    """Test endpoint to verify parser with sample responses"""
    test_cases = [
        '```json {"response": "Moving to coordinates 22, 5.", "command": "move_to", "command_params": {"x": 22, "y": 5}} ```',
        '{"response": "Rotating robot", "command": "rotate", "command_params": {"angle": 90}}',
        'The command is move_to with x=10 and y=20',
        'Invalid response format here'
    ]
    
    results = []
    for test in test_cases:
        parsed = parse_llm_response(test)
        results.append({"input": test, "parsed": parsed})
    
    return {"test_results": results}