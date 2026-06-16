<div align="center">
  <h1>⚙️ AGENTERN</h1>
</div>

The local agent that acts like an intern, but actually checks its **own** work.



## Introduction

Agentern is a local API proxy designed to operate as a drop-in replacement for standard OpenAI-compatible endpoints. It intercepts standard chat and coding requests and routes them through a strict, single-threaded Plan &rarr; Write &rarr; Critique agentic loop. 

This project provides a completely private, API-key free method to interact with local Large Language Models. By acting as a middleware layer over Ollama, it forces smaller, localized models to execute structured reasoning tasks before returning a final output.

## Hardware Requirements & Model Selection

You must install Ollama and pull the appropriate models for your hardware prior to deployment. Operating local models requires balancing parameter size, context window length, and VRAM availability.

| GPU Hardware | VRAM | Recommended Parameter Size | Example Models | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **RTX 3060** | 12GB | 7B - 9B | `qwen2.5-coder:7b`, `llama3.1:8b`, `llava` | Fits Q4_K_M to Q8_0 quantizations comfortably while leaving room for the Agentern RAG context window. |
| **RTX 3090** | 24GB | 14B - 32B | `qwen2.5-coder:32b`, `deepseek-coder-v2` | Fits heavier quantizations of mid-tier models. Can handle massive context windows for whole-codebase RAG ingestion. |

## Ollama Basics

Agentern requires an active installation of Ollama on the host machine.

**1. Install Ollama (Linux):**
```bash
curl -fsSL [https://ollama.com/install.sh](https://ollama.com/install.sh) | sh
```

**2. Pull Required Models:**
```bash
ollama pull qwen2.5-coder:7b
ollama pull llava
ollama pull deepseek-coder-v2
ollama pull llama3.1:8b
```

Pull as many or as few models as you need for your setup.

---

## Automated Deployment (`deploy.sh`)

The repository includes a `deploy.sh` script to automate the network configuration and container orchestration. 

**What the script achieves:**
1. Injects a systemd override to bind Ollama to all network interfaces (`0.0.0.0`), allowing Docker containers to reach it.
2. Restarts the Ollama daemon to apply the new network binding.
3. Builds and launches the Agentern API Docker container.
4. Deploys Open WebUI pre-configured with the specific Docker bridge IP (`172.17.0.1`) to automatically discover both your native Ollama models and the `agentern-` prefixed proxy models.

**Execution:**
```bash
chmod +x deploy.sh
./deploy.sh
```
Access the interface at `http://localhost:17110`.

---

## Manual Configuration Guide

If you prefer to deploy the environment manually or need to troubleshoot network isolation, follow these explicit steps.

### 1. Update Ollama Network Binding
By default, Ollama only listens on the local loopback (`127.0.0.1`). It must be exposed to the Docker bridge network.

Open the systemd service file:
```bash
sudo nano /etc/systemd/system/ollama.service
```

Add the `Environment` variable directly beneath the `[Service]` block:
```ini
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="OLLAMA_HOST=0.0.0.0"

[Install]
WantedBy=default.target
```

Apply the changes:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### 2. Run the Agentern Container
The Agentern API must map its internal network requests to the Docker host bridge IP so it can query the Ollama model tags.

Execute the build and deployment from the project root:
```bash
# Ensure the docker-compose.yml uses OLLAMA_URL=[http://172.17.0.1:11434/api/generate](http://172.17.0.1:11434/api/generate)
docker compose up --build -d
```

### 3. Run Open WebUI
To view and interact with both the standard hardware models and the Agentern proxy loop, instantiate Open WebUI with explicit routing variables.

```bash
docker run -d -p 17110:8080 \
  --add-host=host.docker.internal:host-gateway \
  -e OLLAMA_BASE_URL=[http://172.17.0.1:11434](http://172.17.0.1:11434) \
  -e OPENAI_API_BASE_URL=[http://172.17.0.1:17111/v1](http://172.17.0.1:17111/v1) \
  -e OPENAI_API_KEY=agentern \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

### 4. Configure the Continue IDE Plugin
To utilize your local models directly within VSCodium or VSCode via the Continue plugin, update the `config.json` file. Because VSCodium runs natively on the host machine (not inside a container), it can target `localhost` directly.

Open your `~/.continue/config.json` and add the following to the `models` array:

```json
{
  "models": [
    {
      "title": "Local Qwen Coder",
      "provider": "ollama",
      "model": "qwen2.5-coder:7b",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "Agentern Proxy Loop",
      "provider": "openai",
      "model": "agentern-qwen2.5-coder:7b",
      "apiKey": "agentern",
      "apiBase": "http://localhost:17111/v1"
    }
  ]
}
```

## Performance Evaluation & Benchmarking

The system includes an automated evaluation suite (`evaluate_system.py`) to benchmark your local model library against the Agentern orchestrated pipeline. 

### How the Evaluation Script Works

The evaluation tool automates a side-by-side performance comparison to measure the latency overhead and quality changes introduced by the agent loop:

1. **Dynamic Model Discovery:** It queries the host Ollama inventory endpoint (`/api/tags`) at runtime to automatically identify all local models currently available. Non-text multimodal models (like `llava`) are safely bypassed.
2. **Raw Model Execution:** The script passes a standardized prompt directly to the discovered Ollama model with text-streaming disabled, measuring exactly how long the base model takes to compile a single response.
3. **Agentern Loop Orchestration:** The script then initializes an isolated `AgentLoop` instance passing the same model identifier. The task passes through the entire multi-stage state machine (Triage &rarr; Planning &rarr; Plan Audit &rarr; Generation &rarr; Quality Review Cycles).
4. **Automated Report Compilation:** The script creates an `eval_reports/` directory on your host volume workspace. For each model tested, it generates an isolated Markdown report document containing latency metrics, the exact speed delta, and the raw side-by-side output content blocks.

### Execution

Run the evaluation script directly inside the active service container:

```bash
docker exec -it agentern python /app/evaluate_system.py
```
### Reviewing the Results

Once complete, navigate to the newly generated reports directory in your local workspace to analyze the markdown metrics:

```
ls -l app/eval_reports/
cat app/eval_reports/comparison_qwen2-5-coder_7b.md
```