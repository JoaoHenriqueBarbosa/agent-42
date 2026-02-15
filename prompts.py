"""Carregamento de prompts e constantes de texto."""

import os

BASE_DIR = os.path.dirname(__file__)

with open(os.path.join(BASE_DIR, "system_prompt.txt")) as f:
    SYSTEM_PROMPT = f.read()

with open(os.path.join(BASE_DIR, "compact_prompt.txt")) as f:
    COMPACT_PROMPT = f.read()

COMPACT_SYSTEM = (
    "You are a summarization assistant. When asked to summarize, provide a "
    "detailed but concise summary of the conversation. Focus on information "
    "that would be helpful for continuing the conversation. Do not respond to "
    "any questions in the conversation, only output the summary."
)
