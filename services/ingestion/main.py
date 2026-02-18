import hashlib
import os
import shutil
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import fitz # PyMuPDF

app = FastAPI(title="Ason Document Ingestion Service")

# --- Configuration ---
UPLOAD_DIR = "/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Data Models ---

class DocumentMetadata(BaseModel):
    filename: str
    content_hash: str
    page_count: int
    size_bytes: int

class IngestResponse(BaseModel):
    document_id: str
    metadata: DocumentMetadata
    status: str

# --- Logic ---

def compute_file_hash(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def extract_text_from_pdf(file_path: str) -> List[str]:
    """Extracts text per page."""
    doc = fitz.open(file_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    return pages

# --- Endpoints ---

@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    # 1. Save File
    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # 2. Compute Hash (Chain of Custody)
    content_hash = compute_file_hash(temp_path)
    
    # 3. Rename to Hash to prevent duplicates/collisions
    final_path = os.path.join(UPLOAD_DIR, f"{content_hash}.pdf")
    if not os.path.exists(final_path):
        os.rename(temp_path, final_path)
    else:
        os.remove(temp_path) # Deduplicate

    # 4. Extract Content (Mocking complex OCR/Layout analysis)
    pages = extract_text_from_pdf(final_path)
    
    # 5. Generate Embeddings (Mock - In prod, call Ason-Embedding service)
    # This step would chunk the text and send to the Vector DB
    print(f"Ingesting {len(pages)} pages for {file.filename}")

    # 6. Return Metadata
    return IngestResponse(
        document_id=content_hash, # Using hash as ID for simplicity in this demo
        metadata=DocumentMetadata(
            filename=file.filename,
            content_hash=content_hash,
            page_count=len(pages),
            size_bytes=os.path.getsize(final_path)
        ),
        status="processed"
    )

@app.get("/health")
def health_check():
    return {"status": "ready"}
