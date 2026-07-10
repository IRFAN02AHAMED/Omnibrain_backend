# """

# ai_agent.py — AI Layer: Gemini + Hugging Face + PostgreSQL pgvector

# ==================================================================

# This file manages AI-related logic for Ask Docs.

# What this file does:

#   - Uses Gemini 2.5 Flash as the primary chat model
#   - Uses Hugging Face Qwen/Qwen3-8B as backup chat model

#   - Uses Gemini embedding model as the primary embedding provider
#   - Uses Hugging Face all-mpnet-base-v2 as backup embedding provider

#   - Converts text into 768-dimension embeddings
#   - Builds prompts using retrieved chunks from PostgreSQL
#   - Parses AI JSON responses safely

# Important:

#   - Vector search is done inside PostgreSQL using pgvector.

# """

# import asyncio
# import json
# import re
# from functools import lru_cache
# from typing import AsyncIterator, List

# from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
# from langchain.schema import HumanMessage, SystemMessage

# from app.ai.prompts.assistant_prompt import ASSISTANT_PROMPT_TEMPLATE, build_context_block
# from app.ai.prompts.system_prompt import SYSTEM_PROMPT
# from app.ai.prompts.validation_prompt import VALIDATION_PROMPT_TEMPLATE
# from app.ai.huggingface_embeddings import generate_huggingface_embeddings
# from app.ai.huggingface_chat import generate_huggingface_chat_response
# from app.core.config import settings
# from app.core.logger import logger

# from app.schemas.schemas import AIParsedResponse , AIAnswerFromChunksResponse


# # ─────────────────────────────────────────────────────────────────────────────
# # GEMINI CLIENTS
# # ─────────────────────────────────────────────────────────────────────────────

# @lru_cache(maxsize=1)
# def get_llm() -> ChatGoogleGenerativeAI:
#     """Creates Gemini 2.5 Flash client only when it is first needed."""
#     logger.info(f"[AIAgent] Loading Gemini model: {settings.GEMINI_MODEL}")
#     return ChatGoogleGenerativeAI(
#         model=settings.GEMINI_MODEL,
#         google_api_key=settings.GEMINI_API_KEY,
#         temperature=0.1,
#         max_retries=settings.GEMINI_MAX_RETRIES,
#         timeout=settings.GEMINI_TIMEOUT_SECONDS,
#     )


# @lru_cache(maxsize=1)
# def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
#     """
#     Creates Google embedding client only when it is first needed.

#     We use Gemini embedding model.
#     By default, gemini-embedding-001 may return 3072 dimensions.
#     So we request 768 dimensions because PostgreSQL uses vector(768).
#     """
#     logger.info(f"[AIAgent] Loading embedding model: {settings.GEMINI_EMBEDDING_MODEL}")

#     return GoogleGenerativeAIEmbeddings(
#         model=settings.GEMINI_EMBEDDING_MODEL,
#         google_api_key=settings.GEMINI_API_KEY,
#         output_dimensionality=settings.EMBEDDING_DIMENSIONS,
#     )


# # ─────────────────────────────────────────────────────────────────────────────
# # EMBEDDINGS
# # ─────────────────────────────────────────────────────────────────────────────

# async def generate_gemini_embeddings(texts: List[str]) -> List[List[float]]:
#     """
#     Converts a list of text strings into embeddings.

#     Args:
#         texts: List of chunk texts or question text.

#     Returns:
#         List of vectors. Each vector has 768 float values.
#     """
#     if not texts:
#         return []

#     logger.debug(f"[AIAgent] Generating embeddings for {len(texts)} text item(s)")

#     loop = asyncio.get_event_loop()
#     model = get_embedding_model()

#     embeddings = await loop.run_in_executor(  #loop.run_in_executor(...) runs that blocking work in a separate thread.
#         None,   #Use Python's default thread pool executor.
#         lambda: model.embed_documents(
#             texts,
#             output_dimensionality=settings.EMBEDDING_DIMENSIONS,
#         ),
#     )

#     """
#     If we use this embed_documents it can't we awaited since it is a blocking function.
#     So we use loop.run_in_executor(...) to run that blocking work in a separate thread.
#     """

#     for emb in embeddings:
#         if len(emb) != settings.EMBEDDING_DIMENSIONS:
#             raise ValueError(
#                 f"Embedding dimension mismatch. Expected {settings.EMBEDDING_DIMENSIONS}, got {len(emb)}."
#             )

#     return embeddings

# async def generate_embeddings(texts: List[str]) -> List[List[float]]:
#     """
#     Main embedding function used by the project.

#     First tries Gemini embedding.
#     If Gemini fails because of quota/error, it tries Hugging Face embedding.
#     """

#     try:
#         logger.info("[AIAgent] Trying Gemini embedding provider")
#         return await generate_gemini_embeddings(texts)

#     except Exception as gemini_error:
#         logger.warning(
#             f"[AIAgent] Gemini embedding failed. "
#             f"Trying Hugging Face backup. Error: {gemini_error}"
#         )

#         return await generate_huggingface_embeddings(texts)


# async def generate_query_embedding(question: str) -> List[float]:
#     """Converts one user question into a 768-dimension embedding."""
#     embeddings = await generate_embeddings([question])
#     return embeddings[0]   #because generate_embeddings returns a list of embeddings, but we only have one question, so we return the first embedding.


# # ─────────────────────────────────────────────────────────────────────────────
# # ANSWER GENERATION
# # ─────────────────────────────────────────────────────────────────────────────

# def _parse_json_response(raw_text: str) -> dict:
#     fallback = {
#         "answer": raw_text.strip() if raw_text else "The AI did not return a response. Please try again.",
#         "sources": [],
#         "confidence_score": 0.5 if raw_text else 0.0,
#         "follow_up_questions": [],
#         "has_answer": bool(raw_text),
#     }

#     if not raw_text:
#         return fallback

#     cleaned = re.sub(r"```(?:json)?", "", raw_text).strip().rstrip("`").strip()

#     try:
#         parsed_data = json.loads(cleaned)    #to dict
#         parsed = AIParsedResponse(**parsed_data)
#         return parsed.model_dump() #model_dump() converts the Pydantic object back into a normal Python dictionary.
 
#     except json.JSONDecodeError:
#         logger.warning("[AIAgent] AI response was not valid JSON. Saving raw answer text.")
#         return fallback

#     except Exception as exc:
#         logger.warning(f"[AIAgent] AI response JSON validation failed: {exc}")
#         return fallback

# async def generate_gemini_chat_response(
#     system_prompt: str,
#     user_prompt: str,
# ) -> str:
#     """
#     Generates answer using Gemini chat model.
#     This is the primary chat provider.
#     """
#     loop = asyncio.get_event_loop()
#     llm = get_llm()

#     messages = [
#         SystemMessage(content=system_prompt),
#         HumanMessage(content=user_prompt),
#     ]

#     response = await loop.run_in_executor(None, lambda: llm.invoke(messages))
#     return response.content.strip() if response and response.content else ""


# async def generate_document_summary(
#     document_text: str,
#     log_response: bool = False,
# ) -> str:
#     """
#     Generates a document summary without creating AI logs.
#     """
#     prompt = f"""
#     Give detailed description of the document.

#     Read the following document content and write a long and detailed plain text description of this document/project. Explain what it is about, its purpose, important modules, workflow, technologies, architecture, roles, database or API flow if mentioned, and how it helps the user. Write it for someone opening the document for the first time. Do not use markdown, headings, bullet points, tables, bold text, or code blocks. Use normal plain text only. Keep the answer in 2 to 4 detailed paragraphs.

#     Document content:
#     {document_text}
#     """
#     return await generate_chat_response(
#         system_prompt="You are an expert document summarizer. Give a detailed and comprehensive description of the document.",
#         user_prompt=prompt,
#     )


# async def generate_chat_response(
#     system_prompt: str,
#     user_prompt: str,
# ) -> str:
#     """
#     Main chat function used by Ask Docs.

#     First tries Gemini.
#     If Gemini fails because of quota/API error, it tries Hugging Face.
#     """

#     try:
#         logger.info("[AIAgent] Trying Gemini chat provider")
#         return await generate_gemini_chat_response(
#             system_prompt=system_prompt,
#             user_prompt=user_prompt,
#         )

#     except Exception as gemini_error:
#         logger.warning(
#             f"[AIAgent] Gemini chat failed. "
#             f"Trying Hugging Face backup. Error: {gemini_error}"
#         )

#         return await generate_huggingface_chat_response(
#             system_prompt=system_prompt,
#             user_prompt=user_prompt,
#         )

# async def answer_question_from_chunks(question: str, context_chunks: List[dict]) -> dict:
#     logger.info(f"[AIAgent] Answering question using {len(context_chunks)} retrieved chunk(s)")

#     if not context_chunks:
#         response = AIAnswerFromChunksResponse(
#             answer="The uploaded documents do not contain enough information to answer this question.",
#             sources=[],
#             confidence_score=0.0,
#             follow_up_questions=[],
#             has_answer=False,
#             retrieved_chunks=[],
#             prompt_text=question,
#             raw_response=None,
#         )
#         return response.model_dump()

#     context_block = build_context_block(context_chunks)

#     prompt = ASSISTANT_PROMPT_TEMPLATE.format(
#         question=question,
#         context=context_block,
#     )

#     raw = await generate_chat_response(
#         system_prompt=SYSTEM_PROMPT,
#         user_prompt=prompt,
#     )

#     parsed = AIParsedResponse(**_parse_json_response(raw))

#     response = AIAnswerFromChunksResponse(
#         answer=parsed.answer,
#         sources=parsed.sources,
#         confidence_score=parsed.confidence_score,
#         follow_up_questions=parsed.follow_up_questions,
#         has_answer=parsed.has_answer,
#         retrieved_chunks=context_chunks,
#         prompt_text=prompt,
#         raw_response=raw,
#     )

#     return response.model_dump()

# async def stream_answer_from_chunks(question: str, context_chunks: List[dict]) -> AsyncIterator[str]:
#     """
#     Streams an answer.

#     First tries Gemini streaming.
#     If Gemini streaming fails, it falls back to Hugging Face Qwen.
#     Hugging Face fallback returns the full answer as one chunk.
#     """
#     context_block = build_context_block(context_chunks)
#     prompt = ASSISTANT_PROMPT_TEMPLATE.format(question=question, context=context_block)

#     messages = [
#         SystemMessage(content=SYSTEM_PROMPT),
#         HumanMessage(content=prompt),
#     ]

#     try:
#         logger.info("[AIAgent] Trying Gemini streaming provider")

#         async for chunk in get_llm().astream(messages):
#             if chunk.content:
#                 yield chunk.content

#     except Exception as gemini_error:
#         logger.warning(
#             f"[AIAgent] Gemini streaming failed. "
#             f"Trying Hugging Face Qwen backup. Error: {gemini_error}"
#         )

#         try:
#             qwen_answer = await generate_huggingface_chat_response(
#                 system_prompt=SYSTEM_PROMPT,
#                 user_prompt=prompt,
#             )

#             yield qwen_answer

#         except Exception as hf_error:
#             logger.error(f"[AIAgent] Hugging Face streaming fallback failed: {hf_error}", exc_info=True)
#             yield f"\n[Error: {str(hf_error)}]"


# async def validate_ai_response(question: str, answer: str, context_chunks: List[dict]) -> dict:
#     """
#     Uses AI to validate whether the answer is grounded in the retrieved chunks.
#     Gemini is primary. Hugging Face is backup.
#     """
#     logger.debug("[AIAgent] Running answer validation")

#     context_block = build_context_block(context_chunks)
#     prompt = VALIDATION_PROMPT_TEMPLATE.format(
#         question=question,
#         answer=answer,
#         context=context_block,
#     )

#     try:
#         raw = await generate_chat_response(
#             system_prompt="You are an AI response validator. Return only valid JSON.",
#             user_prompt=prompt,
#         )

#         cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
#         return json.loads(cleaned)

#     except Exception as exc:
#         logger.error(f"[AIAgent] Validation failed: {exc}", exc_info=True)
#         return {
#             "is_valid": True,
#             "failed_criteria": [],
#             "validation_notes": f"Validation check failed: {str(exc)}",
#             "suggested_correction": None,
#         }

# async def stream_question(question: str) -> AsyncIterator[str]:
#     """
#     Backward-compatible simple streaming helper.

#     Note: This does not do source saving. The normal /qa/ask endpoint should be
#     used for the complete RAG flow with source references and database history.
#     """
#     async for token in stream_answer_from_chunks(question, []):
#         yield token
