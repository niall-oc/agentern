import argparse
import os
import time
import requests
import asyncio
import yaml
from agent import AgentLoop

def get_installed_models(ollama_url: str):
    """Fetch the list of available models from the host Ollama instance."""
    try:
        response = requests.get(f"{ollama_url.rstrip('/')}/api/tags")
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            return [m["name"] for m in models_data]
    except Exception as e:
        print(f"Error connecting to Ollama to fetch models: {e}")
    return []

async def evaluate_model_comparison(model_name, test_task, agent_config, ollama_url, output_path, db_path=None):
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
        raw_response = requests.post(f"{ollama_url.rstrip('/')}/api/generate", json=raw_payload)
        if raw_response.status_code == 200:
            raw_output = raw_response.json().get("response", "Error: No response key.")
        else:
            raw_output = f"Raw LLM returned status {raw_response.status_code}"
    except Exception as e:
        raw_output = f"Raw call failed: {str(e)}"
    raw_time = time.time() - start_raw

    # 2. Agentern Orchestration Execution
    agent_engine = AgentLoop(model_name, agent_config, ollama_url, db_path=db_path)
    
    start_agent = time.time()
    try:
        agent_output = await agent_engine.run_loop(test_task)
    except Exception as e:
        agent_output = f"Agentern loop failed: {str(e)}"
    agent_time = time.time() - start_agent

    # 3. Write individual report files
    safe_model_name = model_name.replace(":", "_").replace(".", "-")
    
    # Raw model output file
    raw_file = os.path.join(output_path, f"{safe_model_name}.md")
    with open(raw_file, "w", encoding="utf-8") as f:
        f.write(f"# {model_name} — Evaluation\n\n")
        f.write(f"## Prompt\n{test_task}\n\n")
        f.write(f"## Runtime\n{raw_time:.2f} seconds\n\n")
        f.write(f"## Thinking / Output\n\n{raw_output}\n")
    print(f"  Raw model report  : {raw_file}")

    # Agent output file
    agent_file = os.path.join(output_path, f"agent_{safe_model_name}.md")
    with open(agent_file, "w", encoding="utf-8") as f:
        f.write(f"# Agentern + {model_name} — Evaluation\n\n")
        f.write(f"## Prompt\n{test_task}\n\n")
        f.write(f"## Runtime\n{agent_time:.2f} seconds\n\n")
        f.write(f"## Thinking / Output\n\n{agent_output}\n")
    print(f"  Agent report      : {agent_file}")

async def main(test_task: str, agent_config: dict, ollama_url: str, output_path: str, db_path: str = ""):
    """Run evaluation across available Ollama models.

    :param test_task: A natural-language question or task prompt to test.
    :param agent_config: The parsed agent definition dictionary (from a YAML file).
    :param ollama_url: Base URL of the Ollama instance.
    :param output_path: Directory to write evaluation report files into.
    :param db_path: Optional path to a ChromaDB vector store to provide
        retrieval-augmented context to the agent.  Leave empty to disable.
    """
    os.makedirs(output_path, exist_ok=True)

    models = get_installed_models(ollama_url)
    if not models:
        print("No models detected from Ollama. Exiting evaluation.")
        return
        
    print(f"Detected models for evaluation: {models}")
    
    for model in models:
        if "llava" in model or "minicpm" in model:
            print(f"Skipping multimodal model: {model}")
            continue

        await evaluate_model_comparison(
            model, test_task, agent_config, ollama_url, output_path,
            db_path=db_path if db_path else None
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare raw Ollama model output against Agentern orchestrated output.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --test_task=\"Write a Fastify CRUD\"            \\n"
            "  %(prog)s --test_task=\"Explain async/await\"             \\n"
            "  %(prog)s --test_task=\"What is the time?\"              \\n"
            "         --agent_config=./my_agent.yaml                     \\n"
            "         --db_path=./chroma_data                            \n"
        ),
    )

    parser.add_argument(
        "--test_task",
        type=str,
        required=True,
        help=(
            "The natural-language question or task prompt to test. "
            "This is passed both to the raw model (direct generation) "
            "and to the Agentern loop (tool-augmented orchestration)."
        ),
        metavar="PROMPT",
    )

    parser.add_argument(
        "--agent_config",
        type=str,
        required=True,
        help=(
            "Path to a YAML file containing the agent definition. "
            "The file should define the system prompt, available tools, "
            "and other orchestration parameters used by Agentern."
        ),
        metavar="FILE",
    )

    parser.add_argument(
        "--ollama_url",
        type=str,
        required=True,
        help=(
            "Base URL of the Ollama instance (e.g. "
            "http://172.17.0.1:11434 or http://localhost:11434). "
            "Used to fetch the list of installed models and "
            "to send inference requests."
        ),
        metavar="URL",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=".",
        help=(
            "Directory to write evaluation report files into. "
            "Defaults to the current directory."
        ),
        metavar="DIR",
    )

    parser.add_argument(
        "--db_path",
        type=str,
        default="",
        help=(
            "Optional path to a ChromaDB vector store directory. "
            "If provided, the agent will use retrieval-augmented "
            "generation (RAG) to search relevant code context. "
            "Omit or leave empty to disable RAG."
        ),
        metavar="PATH",
    )

    args = parser.parse_args()

    # Resolve paths
    agent_config_path = os.path.abspath(args.agent_config)
    output_path = os.path.abspath(args.output)
    db_path = os.path.abspath(args.db_path) if args.db_path else ""
    ollama_url = args.ollama_url.rstrip("/")

    if not os.path.isfile(agent_config_path):
        parser.error(f"agent_config file not found: {agent_config_path}")

    if args.db_path and not os.path.isdir(db_path):
        parser.error(f"db_path does not exist or is not a directory: {db_path}")

    # Load the YAML agent config
    with open(agent_config_path) as f:
        agent_config = yaml.safe_load(f)

    print(f"Test task     : {args.test_task}")
    print(f"Agent config  : {agent_config_path}")
    print(f"Ollama URL    : {ollama_url}")
    print(f"Output dir    : {output_path}")
    print(f"ChromaDB path : {db_path if db_path else '(not provided)'}")
    print()

    asyncio.run(main(
        test_task=args.test_task,
        agent_config=agent_config,
        ollama_url=ollama_url,
        output_path=output_path,
        db_path=db_path,
    ))

    print()
    print(f"Evaluation complete.  Reports saved to {output_path}/.")