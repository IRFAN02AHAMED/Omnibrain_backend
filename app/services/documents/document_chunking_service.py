import hashlib
from typing import List, Dict, Any
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from app.ai.ai_agent import generate_embeddings

# Mock embedding for now since ai_agent is commented until Phase 8
async def generate_mock_embedding(text: str) -> List[float]:
    # returns 768-dim mock vector
    return [0.0] * 768

async def chunk_and_embed_text(text: str) -> List[Dict[str, Any]]:
    # Very simple chunking for now until Langchain text splitters are activated
    chunk_size = 1000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size) if text[i:i+chunk_size].strip()]
    
    result = []
    for i, chunk_text in enumerate(chunks):
        embedding = await generate_mock_embedding(chunk_text)
        result.append({
            "chunk_index": i,
            "chunk_text": chunk_text,
            "token_count": len(chunk_text) // 4,
            "embedding": embedding
        })
    return result

def calculate_checksum(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()
