import os
import time
import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from agent import AgentLoop
import yaml

app = FastAPI(title="Agentern API")

with open('agent.yaml') as f:
    agent_config = yaml.safe_load(f)

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False

@app.get("/v1/models")
async def list_models():
    # Derive the base Ollama URL to query available tags
    ollama_url = os.getenv("OLLAMA_URL")
    tags_url = f"{ollama_url.rstrip('/')}/api/tags"
    
    models_data = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(tags_url)
            if res.status_code == 200:
                for m in res.json().get("models", []):
                    # Prefix with 'agentern-' so you know it routes through the loop
                    models_data.append({
                        "id": f"agentern-{m['name']}",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "agentern"
                    })
    except Exception as e:
        print(f"Error fetching models from Ollama: {e}")
        
    if not models_data:
        models_data = [{
            "id": "agentern-fallback-model",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "agentern"
        }]
        
    return {"object": "list", "data": models_data}

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # Extract the latest user requirement
    user_msg = next((m.content for m in reversed(request.messages) if m.role == 'user'), "")
    
    # Strip the 'agentern-' prefix to pass the correct target model to Ollama
    target_model = request.model.replace("agentern-", "") if request.model.startswith("agentern-") else request.model
    
    # Instantiate a specific loop tied to the user's selected model
    ollama_url = os.getenv("OLLAMA_URL")
    base_url = ollama_url.rstrip('/')
    db_path = os.getenv("CHROMADB_PATH", None)
    request_loop = AgentLoop(target_model, agent_config, base_url, db_path=db_path)
    
    if request.stream:
        return StreamingResponse(request_loop.stream_loop(user_msg), media_type="text/event-stream")
    else:
        final_response = await request_loop.run_loop(user_msg)
        return JSONResponse({
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": final_response}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        })