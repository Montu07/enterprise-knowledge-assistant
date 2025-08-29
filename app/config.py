import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")

# Safety check
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found in .env file. Please add it.")
