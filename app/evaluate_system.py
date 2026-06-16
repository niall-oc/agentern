import os
import time
import requests
import asyncio
from agent.loop import AgentLoop

def get_installed_models():
    """Fetch the list of available models from the host Ollama instance."""
    try:
        response = requests.get("http://172.17.0.1:11434/api/tags")
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            return [m["name"] for m in models_data]
    except Exception as e:
        print(f"Error connecting to Ollama to fetch models: {e}")
    return []

async def evaluate_model_comparison(model_name, test_task):
    print(f"\nEvaluating Model: {model_name}")
    print("-" * 50)
    
    # 1. Raw Model Execution
    raw_payload = {
        "model": model_name,
        "prompt": test_task,
        "stream": False
    }
    
    start_raw = time.time()
    try:
        raw_response = requests.post("http://172.17.0.1:11434/api/generate", json=raw_payload)
        if raw_response.status_code == 200:
            raw_output = raw_response.json().get("response", "Error: No response key.")
        else:
            raw_output = f"Raw LLM returned status {raw_response.status_code}"
    except Exception as e:
        raw_output = f"Raw call failed: {str(e)}"
    raw_time = time.time() - start_raw

    # 2. Agentern Orchestration Execution
    agent_engine = AgentLoop(model=model_name)
    
    start_agent = time.time()
    try:
        agent_output = await agent_engine.run_loop(test_task)
    except Exception as e:
        agent_output = f"Agentern loop failed: {str(e)}"
    agent_time = time.time() - start_agent

    # 3. Write individual report file safely
    safe_model_name = model_name.replace(":", "_").replace(".", "-")
    file_name = f"eval_reports/comparison_{safe_model_name}.md"
    
    # Use triple quotes for text blocks but avoid literal backticks inside variables
    ticks = "```"
    
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(f"# Evaluation Report: {model_name} vs Agentern System\n\n")
        f.write(f"## Test Prompt\n> {test_task}\n\n")
        f.write(f"### Performance Metrics\n")
        f.write(f"* **Raw Model Latency:** {raw_time:.2f} seconds\n")
        f.write(f"* **Agentern System Latency:** {agent_time:.2f} seconds\n")
        f.write(f"* **Latency Delta:** {agent_time - raw_time:.2f} seconds\n\n")
        f.write(f"---\n\n## Raw {model_name} Generation Output\n\n")
        f.write(f"{ticks}text\n{raw_output}\n{ticks}\n\n")
        f.write(f"---\n\n## Agentern System Orchestrated Output\n\n")
        f.write(f"{ticks}text\n{agent_output}\n{ticks}\n")
        
    print(f"Saved report: {file_name}")

async def main():
    test_task = "Write a Fastify CRUD configuration targeting our standard MariaDB schema parameters."
    
    os.makedirs("eval_reports", exist_ok=True)
    
    models = get_installed_models()
    if not models:
        print("No models detected from Ollama. Exiting evaluation.")
        return
        
    print(f"Detected models for evaluation: {models}")
    
    for model in models:
        if "llava" in model or "minicpm" in model:
            print(f"Skipping multimodal model: {model}")
            continue
            
        await evaluate_model_comparison(model, test_task)

if __name__ == "__main__":
    asyncio.run(main())