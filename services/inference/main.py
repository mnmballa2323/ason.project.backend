import hashlib
import json
import time
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from vllm import LLM, SamplingParams

app = FastAPI(title="Ason Deterministic Inference Engine")

# --- Configuration ---
MODEL_PATH = "/models/ason-72b-instruct" # Logic path in container
# In production, we would initialize the LLM engine here. 
# For build verification, we mock the engine if GPU is not available during build.
try:
    llm_engine = LLM(model=MODEL_PATH, trust_remote_code=True, dtype="half", enforce_eager=True)
except Exception as e:
    print(f"WARNING: Could not load vLLM engine (expected during build without GPU): {e}")
    llm_engine = None

# --- Data Models ---

class InferenceRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    seed: int = Field(..., description="Mandatory seed for determinism")
    max_tokens: int = Field(default=4096, le=8192)
    stop_sequences: List[str] = []

class InferenceSnapshot(BaseModel):
    request_hash: str
    model_version: str
    inputs: InferenceRequest
    hyperparameters: Dict[str, Any]
    output_text: str
    output_hash: str
    timestamp: float

# --- Determinism Logic ---

def get_deterministic_sampling_params(seed: int, max_tokens: int, stop_sequences: List[str]) -> SamplingParams:
    """
    Returns strict sampling parameters for Ason-72B determinism.
    """
    return SamplingParams(
        n=1,
        temperature=0.0,      # Greedy decoding
        top_p=1.0,            # Disable nucleus sampling
        top_k=-1,             # Disable top-k sampling
        seed=seed,            # Server-side seed enforcement
        max_tokens=max_tokens,
        stop=stop_sequences,
        ignore_eos=False
    )

def compute_hash(data: Any) -> str:
    """Computes SHA-256 hash of a JSON-serializable object."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

# --- Endpoints ---

@app.post("/generate", response_model=InferenceSnapshot)
async def generate_text(request: InferenceRequest):
    if not llm_engine:
        raise HTTPException(status_code=503, detail="Inference engine not ready (GPU missing?)")

    # 1. Construct Prompt (Ason Chat Format)
    # Note: Ason-72B-Instruct uses ChatML format usually handled by tokenizer.apply_chat_template
    # Here we simulate the raw prompt structure for transparency.
    messages = [
        {"role": "system", "content": request.system_prompt},
        {"role": "user", "content": request.user_prompt}
    ]
    
    # 2. Configure Sampling
    sampling_params = get_deterministic_sampling_params(
        seed=request.seed,
        max_tokens=request.max_tokens,
        stop_sequences=request.stop_sequences
    )

    # 3. Execute Inference
    # vLLM generate is blocking; in prod use AsyncLLMEngine
    outputs = llm_engine.generate([messages], sampling_params)
    generated_text = outputs[0].outputs[0].text

    # 4. Create Snapshot
    hyperparams = {
        "temperature": sampling_params.temperature,
        "top_p": sampling_params.top_p,
        "seed": sampling_params.seed,
        "model_path": MODEL_PATH
    }
    
    output_hash = hashlib.sha256(generated_text.encode("utf-8")).hexdigest()
    
    snapshot = InferenceSnapshot(
        request_hash=compute_hash(request.dict()),
        model_version="ason-72b-instruct-v1.0", # Configuration driven
        inputs=request,
        hyperparameters=hyperparams,
        output_text=generated_text,
        output_hash=output_hash,
        timestamp=time.time()
    )

    # 5. Log Snapshot (In a real system, send this to the Audit Service queue)
    # print(f"AUDIT_LOG: {snapshot.json()}")

    return snapshot

@app.get("/health")
def health_check():
    return {"status": "ready" if llm_engine else "mock_mode", "model": MODEL_PATH}
