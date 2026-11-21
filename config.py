import os

from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL_ID = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
