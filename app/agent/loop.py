import httpx
import json
import os
from app.prompts import get_prompt
from app.vector.chroma import VectorStore

class AgentLoop:
    def __init__(self, model="qwen2.5-coder"):
        # Defaulting to a local Ollama instance on standard port
        self.llm_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.model = model
        self.vector_store = VectorStore()

    async def call_llm(self, system: str, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=180.0) as client:
            res = await client.post(self.llm_url, json={
                "model": self.model,
                "prompt": f"{system}\n\n{prompt}",
                "stream": False
            })
            if res.status_code == 200:
                return res.json().get("response", "")
            return f"Error: LLM returned status {res.status_code}"

    async def run_loop(self, task: str) -> str:
        # Retrieve context from ChromaDB
        context = self.vector_store.search(task)
        
        # Step 1: Plan (Pulling from yaml)
        plan = await self.call_llm(
            get_prompt("PLANNER_PROMPT"), 
            f"Task: {task}\nContext: {context}"
        )
        
        # Step 2: Write (Pulling from yaml)
        code = await self.call_llm(
            get_prompt("WRITER_PROMPT"), 
            f"Task: {task}\nPlan: {plan}\nContext: {context}"
        )
        
        # Step 3: Critique Loop
        max_retries = 2
        for _ in range(max_retries):
            critique = await self.call_llm(
                get_prompt("CRITIQUE_PROMPT"), 
                f"Task: {task}\nCode: {code}"
            )
            if "PASS" in critique.upper():
                break
            
            # Rewrite based on critique feedback. We drop previous chat history 
            # to preserve the context window limit on 8GB/12GB GPUs.
            code = await self.call_llm(
                get_prompt("WRITER_PROMPT"), 
                f"Task: {task}\nFix these issues: {critique}\nCurrent Code: {code}"
            )
            
        return code

    async def stream_loop(self, task: str):
        # Sends intermediary states as streamed text tokens to satisfy UI expectations
        yield f"data: {json.dumps({'choices': [{'delta': {'content': '[Agentern: Planning...]\n'}}]})}\n\n"
        
        # Perform actual execution loop
        final_code = await self.run_loop(task)
        
        yield f"data: {json.dumps({'choices': [{'delta': {'content': final_code}}]})}\n\n"
        yield "data: [DONE]\n\n"