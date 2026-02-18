"""
Cognitive Memory Service — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Implements a local, persistent memory store for the platform.
Simulates the "Memory" capabilities of Ason-Agent using a lightweight
JSON-based vector/keyword store to avoid heavy dependencies.

Features:
- Long-Term Knowledge Storage (Incidents, Resolutions)
- RAG (Retrieval Augmented Generation) for Self-Healing
"""
import json
import logging
import time
import os
import math
import re
from typing import List, Dict, Tuple

logger = logging.getLogger("qwen.memory")

class MemoryEngine:
    """
    Local Cognitive Memory.
    Stores 'experiences' and retrieves them based on keyword similarity.
    """
    
    MEMORY_FILE = "ason_memory.jsonl"
    
    def __init__(self):
        self._memories = []
        self._load_memory()

    def _load_memory(self):
        """Load memory from disk."""
        if not os.path.exists(self.MEMORY_FILE):
            # Seed with some initial "Knowledge"
            self.add_memory("Should restart pod if CPU > 90%", tags=["heuristic", "cpu"])
            self.add_memory("If DB connection fails, check firewall rules first.", tags=["heuristic", "db"])
            return
            
        try:
            with open(self.MEMORY_FILE, "r") as f:
                for line in f:
                    self._memories.append(json.loads(line))
            logger.info(f"Loaded {len(self._memories)} cognitive memories.")
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")

    def add_memory(self, content: str, tags: List[str] = []) -> str:
        """
        Store a new experience.
        """
        timestamp = time.time()
        memory_id = f"mem-{int(timestamp*1000)}"
        
        entry = {
            "id": memory_id,
            "timestamp": timestamp,
            "content": content,
            "tags": tags,
            # In a real system, we would generate an embedding here.
            # For this lightweight version, we tokenize simple keywords.
            "keywords": self._tokenize(content)
        }
        
        self._memories.append(entry)
        
        # Persist
        with open(self.MEMORY_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
            
        logger.info(f"🧠 Learned: {content[:50]}...")
        return memory_id

    def retrieve(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Retrieve relevant memories (RAG).
        Uses simple Jaccard similarity on tokens for simulation.
        """
        query_tokens = set(self._tokenize(query))
        
        scored = []
        for mem in self._memories:
            mem_tokens = set(mem["keywords"])
            if not mem_tokens:
                continue
                
            # Jaccard Similarity
            intersection = query_tokens.intersection(mem_tokens)
            score = len(intersection) / len(query_tokens.union(mem_tokens))
            
            if score > 0:
                scored.append((score, mem))
        
        # Sort by score desc, then recency
        scored.sort(key=lambda x: (x[0], x[1]["timestamp"]), reverse=True)
        
        results = [x[1] for x in scored[:limit]]
        logger.info(f"🔍 Recalled {len(results)} memories for query: '{query}'")
        return results

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer."""
        # Lowercase, remove punctuation, split
        clean = re.sub(r'[^a-z0-9\s]', '', text.lower())
        return clean.split()

    def get_stats(self) -> Dict:
        return {
            "total_memories": len(self._memories),
            "storage_file": self.MEMORY_FILE
        }

# Singleton
memory_engine = MemoryEngine()
