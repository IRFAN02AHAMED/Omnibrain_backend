# """
# assistant_prompt.py — Assistant Prompt Template for Q&A Queries
# ================================================================
# This file provides the template that wraps the user's question
# along with the retrieved document context chunks before sending to Gemini.

# The {question} and {context} placeholders are filled in at runtime
# by the AI service layer.

# IMPORTANT: This is a template string, not a function. Format it with .format()
# """




# ASSISTANT_PROMPT_TEMPLATE = """
# You are answering a question from an employee using the internal Knowledge Base system.

# ═══════════════════════════════════════════════════════════════
# RETRIEVED DOCUMENT CONTEXT
# ═══════════════════════════════════════════════════════════════

# The following document chunks were retrieved as relevant to the user's question.
# Each chunk includes its unique ID, document title, and text content.
# Use ONLY this information to construct your answer.

# {context}

# ═══════════════════════════════════════════════════════════════
# USER QUESTION
# ═══════════════════════════════════════════════════════════════

# {question}

# ═══════════════════════════════════════════════════════════════
# INSTRUCTIONS FOR THIS RESPONSE
# ═══════════════════════════════════════════════════════════════

# 1. Read all context chunks carefully before answering.
# 2. Answer the question directly and completely.
# 3. For every fact in your answer, identify which chunk it came from.
# 4. Include the chunk_id and a short snippet in your sources list.
# 5. Set confidence_score based on how well the context covers the question:
#    - 0.9-1.0: Context directly and fully answers the question
#    - 0.6-0.9: Context partially answers or requires inference
#    - 0.3-0.6: Context is loosely related
#    - 0.0-0.3: Context does not meaningfully address the question
# 6. Suggest 2 follow-up questions the user might benefit from asking.
# 7. Return ONLY the JSON object — no extra text, no markdown fences.
# """.strip()


# def build_context_block(chunks: list[dict]) -> str:
#     """
#     Formats a list of chunk dictionaries into a readable context block
#     that gets injected into the assistant prompt.

#     Args:
#         chunks: List of dicts with keys: chunk_id, document_title, chunk_text, chunk_no

#     Returns:
#         Formatted context string for inclusion in the prompt.

#     Example input:
#         [
#             {
#                 "chunk_id": "abc-123",
#                 "document_title": "Setup Guide",
#                 "chunk_no": 3,
#                 "chunk_text": "To install the app, run npm install..."
#             }
#         ]
#     """
#     if not chunks:
#         return "No relevant document chunks were found for this question."

#     lines = []
#     for i, chunk in enumerate(chunks, start=1):
#         lines.append(
#             f"--- CHUNK {i} ---\n"
#             f"Chunk ID     : {chunk['chunk_id']}\n"
#             f"Document     : {chunk['document_title']}\n"
#             f"Chunk Number : {chunk['chunk_no']}\n"
#             f"Content      :\n{chunk['chunk_text']}\n"
#         )

#     return "\n".join(lines)
