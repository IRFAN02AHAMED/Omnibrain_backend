# import httpx

# from app.core.config import settings
# from app.core.logger import logger


# class HuggingFaceEmbeddingError(Exception):
#     pass


# async def generate_huggingface_embeddings(texts: list[str]) -> list[list[float]]:
#     """
#     Generate 768-dimensional embeddings using Hugging Face API.

#     Model:
#         sentence-transformers/all-mpnet-base-v2

#     This is used as a backup if Gemini embedding quota fails.
#     """

#     if not settings.HUGGINGFACE_API_KEY:
#         raise HuggingFaceEmbeddingError("Hugging Face API key is missing.")

#     if not texts:
#         return []

#     embeddings: list[list[float]] = []

#     url = (
#         "https://router.huggingface.co/hf-inference/models/"
#         f"{settings.HUGGINGFACE_EMBEDDING_MODEL}"
#         "/pipeline/feature-extraction"
#     )

#     headers = {
#         "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
#         "Content-Type": "application/json",
#     }

#     async with httpx.AsyncClient(timeout=60) as client:   #backend to HUGGINGFACE API Call , wait for 60 seconds
#         for text in texts:
#             logger.info("[HF Embedding] Generating embedding using Hugging Face")

#             response = await client.post(
#                 url,
#                 headers=headers,
#                 json={"inputs": text},
#             )

#             if response.status_code >= 400:
#                 raise HuggingFaceEmbeddingError(
#                     f"Hugging Face embedding failed: "
#                     f"{response.status_code} {response.text}"
#                 )

#             data = response.json()

#             embedding = _convert_to_single_embedding(data)

#             if len(embedding) != settings.EMBEDDING_DIMENSIONS:
#                 raise HuggingFaceEmbeddingError(
#                     f"Embedding dimension mismatch. "
#                     f"Expected {settings.EMBEDDING_DIMENSIONS}, got {len(embedding)}."
#                 )

#             embeddings.append(embedding)

#     return embeddings


# def _convert_to_single_embedding(data) -> list[float]:
#     """
#     Hugging Face may return the embedding in different shapes.

#     Possible shapes:
#     1. [0.1, 0.2, ...]
#        Already a single sentence vector.

#     2. [[0.1, ...], [0.2, ...], ...]
#        Token-level vectors. We average them.

#     3. [[[0.1, ...], [0.2, ...], ...]]
#        Batch with one item. We unwrap it, then average.
#     """

#     if not data:
#         raise HuggingFaceEmbeddingError("Empty response from Hugging Face.")

#     # Case 3: batch response with one item
#     if (
#         isinstance(data, list)
#         and data
#         and isinstance(data[0], list)
#         and data[0]
#         and isinstance(data[0][0], list)
#     ):
#         data = data[0]

#     # Case 1: already one vector
#     if isinstance(data, list) and data and isinstance(data[0], (int, float)):
#         return [float(value) for value in data]

#     # Case 2: token vectors, so we do mean pooling (Take average values to combine many vectors into one vector.)
#     if isinstance(data, list) and data and isinstance(data[0], list):
#         token_count = len(data)
#         vector_size = len(data[0])

#         #Each column is one embedding feature.
#         # We want to combine the same feature across all tokens.

#         return [
#             sum(float(token_vector[i]) for token_vector in data) / token_count
#             for i in range(vector_size)
#         ]

#     raise HuggingFaceEmbeddingError("Unexpected Hugging Face response format.")