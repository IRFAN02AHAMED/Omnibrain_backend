# """
# validation_prompt.py — Validation & Evaluation Prompts
# =======================================================
# Contains prompts used to:
#   1. Validate AI responses before saving them (VALIDATION_PROMPT)
#   2. Evaluate answer quality for admin review (EVALUATION_PROMPT)

# These are separate from the main QA flow to keep concerns isolated.
# """


# VALIDATION_PROMPT_TEMPLATE = """
# You are an AI Quality Validator. Your job is to check whether an AI-generated answer
# meets the quality standards of the Knowledge Base system.

# ═══════════════════════════════════════════════════════════════
# ORIGINAL QUESTION
# ═══════════════════════════════════════════════════════════════
# {question}

# ═══════════════════════════════════════════════════════════════
# AI GENERATED ANSWER
# ═══════════════════════════════════════════════════════════════
# {answer}

# ═══════════════════════════════════════════════════════════════
# SOURCE CHUNKS USED
# ═══════════════════════════════════════════════════════════════
# {context}

# ═══════════════════════════════════════════════════════════════
# VALIDATION CRITERIA — CHECK ALL OF THESE
# ═══════════════════════════════════════════════════════════════

# 1. GROUNDED   — Every claim in the answer is supported by the provided context chunks.
# 2. ACCURATE   — The answer does not contradict any content in the source chunks.
# 3. COMPLETE   — The answer fully addresses what the user asked.
# 4. SAFE       — The answer contains no harmful, offensive, or misleading content.
# 5. CITED      — At least one source chunk is cited in the answer.

# ═══════════════════════════════════════════════════════════════
# INSTRUCTIONS
# ═══════════════════════════════════════════════════════════════

# Return ONLY this JSON object:

# {{
#     "is_valid": <true if the answer passes ALL criteria, false otherwise>,
#     "failed_criteria": ["<name of any failed criterion>"],
#     "validation_notes": "<Brief explanation of what passed or failed>",
#     "suggested_correction": "<If is_valid=false, a corrected version of the answer. Otherwise null>"
# }}
# """.strip()


# # EVALUATION_PROMPT_TEMPLATE = """
# # You are an AI Answer Evaluator. Score the quality of the following AI answer
# # for an internal Knowledge Base system.

# # ═══════════════════════════════════════════════════════════════
# # QUESTION
# # ═══════════════════════════════════════════════════════════════
# # {question}

# # ═══════════════════════════════════════════════════════════════
# # ANSWER
# # ═══════════════════════════════════════════════════════════════
# # {answer}

# # ═══════════════════════════════════════════════════════════════
# # EVALUATION DIMENSIONS
# # ═══════════════════════════════════════════════════════════════

# # Score each dimension from 1 (poor) to 5 (excellent):

# # - RELEVANCE  : Does the answer directly address the question?
# # - ACCURACY   : Is the information factually consistent with good practices?
# # - CLARITY    : Is the answer easy to understand?
# # - COMPLETENESS: Does the answer cover all important aspects of the question?
# # - CONCISENESS: Is the answer appropriately brief without missing key points?

# # ═══════════════════════════════════════════════════════════════
# # INSTRUCTIONS
# # ═══════════════════════════════════════════════════════════════

# # Return ONLY this JSON object:

# # {{
# #     "scores": {{
# #         "relevance":    <1-5>,
# #         "accuracy":     <1-5>,
# #         "clarity":      <1-5>,
# #         "completeness": <1-5>,
# #         "conciseness":  <1-5>
# #     }},
# #     "overall_score": <average of above scores, 1 decimal place>,
# #     "strengths":  ["<strength 1>", "<strength 2>"],
# #     "weaknesses": ["<weakness 1>"],
# #     "recommendation": "<improve | accept | reject>"
# # }}
# # """.strip()
