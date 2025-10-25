import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8001))
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # CORS
    ALLOWED_ORIGINS = [FRONTEND_URL, "http://localhost:3000", "http://localhost:5173"]

config = Config()