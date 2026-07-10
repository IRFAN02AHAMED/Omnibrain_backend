# import httpx

# from app.core.config import settings
# from app.core.logger import logger


# class HuggingFaceChatError(Exception):
#     pass


# async def generate_huggingface_chat_response(
#     system_prompt: str,
#     user_prompt: str,
# ) -> str:
#     """
#     Generate answer using Hugging Face chat model.

#     This is used as backup if Gemini chat fails because of quota/error.
#     """

#     if not settings.HUGGINGFACE_API_KEY:
#         raise HuggingFaceChatError("Hugging Face API key is missing.")

#     url = "https://router.huggingface.co/v1/chat/completions"

#     headers = {
#         "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
#         "Content-Type": "application/json",
#     }

#     payload = {
#         "model": settings.HUGGINGFACE_CHAT_MODEL,
#         "messages": [
#             {
#                 "role": "system",
#                 "content": system_prompt,
#             },
#             {
#                 "role": "user",
#                 "content": user_prompt,
#             },
#         ],
#         "temperature": 0.1,
#         "max_tokens": 1200,
#     }

#     async with httpx.AsyncClient(timeout=60) as client:
#         logger.info(
#             f"[HF Chat] Generating answer using Hugging Face model: "
#             f"{settings.HUGGINGFACE_CHAT_MODEL}"
#         )

#         response = await client.post(url, headers=headers, json=payload)

#         if response.status_code >= 400:
#             raise HuggingFaceChatError(
#                 f"Hugging Face chat failed: {response.status_code} {response.text}"
#             )

#         data = response.json()

#     try:
#         return data["choices"][0]["message"]["content"]
#     except Exception as exc:
#         raise HuggingFaceChatError(
#             f"Unexpected Hugging Face chat response format: {data}"
#         ) from exc