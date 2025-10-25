from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import config
from app.services.mcp_service import MCPService
from app.services.gemini_service import GeminiService
from app.services.chat_service import ChatService
from app.api.routes import health, chat
from app.api.websocket import handle_chat_stream

# Global services
mcp_service: MCPService = None
gemini_service: GeminiService = None
chat_service: ChatService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global mcp_service, gemini_service, chat_service
    print("🚀 Starting up...")
    
    mcp_service = MCPService(config.MCP_SERVER_URL)
    await mcp_service.connect()
    
    gemini_service = GeminiService(config.GOOGLE_API_KEY)
    chat_service = ChatService(mcp_service, gemini_service)
    
    # Inject chat service into routes
    chat.chat_service = chat_service
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    await mcp_service.disconnect()

app = FastAPI(
    title="K8s MCP Web API",
    description="Backend for Kubernetes MCP Client with Gemini",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router)
app.include_router(chat.router)

# WebSocket
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await handle_chat_stream(websocket, chat_service)

@app.get("/")
async def root():
    return {"message": "K8s MCP Backend API", "docs": "/docs"}