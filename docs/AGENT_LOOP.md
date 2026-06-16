# Engineering the Core Logic (`app/agent.py`)

The orchestration architecture of Agentern is centered entirely within the `AgentLoop` class inside `app/agent.py`. It establishes a sequential execution environment designed to optimize the performance of local, consumer-tier hardware models.

---

## Structural Architecture

The pipeline manages local state changes over a single asynchronous engine iteration:

```
[User Task] ──> ChromaDB Vector Store (Retrieve Context)
                      │
                      ▼
               Stage 1: Planner  ──> (Generates Execution Strategy)
                      │
                      ▼
               Stage 2: Writer   ──> (Generates Baseline Code)
                      │
    ┌─────────────────▼─────────────────┐
    │          Stage 3: Critic          │
    │  Executes up to 2 retry passes.   │◄───┐
    │  Looks for "PASS" string indicator│    │ (Loop Fix Phase)
    └─────────────────┬─────────────────┘    │
                      │                      │
            [PASS?] ──┼─── No (Re-Write) ────┘
                      │
                     Yes
                      │
                      ▼
         [Final Consolidated Output]
```

---

## State Control Breakdown

### Context Ingestion
Before hitting the LLM, `run_loop(task)` queries your local embeddings store:
```python
context = self.vector_store.search(task)
```
This drops downstream reference variables into both the planning and writing context variables without hard-coding specific string paths into the engine.

### The Self-Correction Loop
The agent enforces a strict `max_retries = 2` constraint. It parses the return value of the `CRITIQUE_PROMPT` execution:
```python
if "PASS" in critique.upper():
    break
```
If the token `"PASS"` is missing, it strips the context history and loops back into the writer using the critique text as a patch constraint.

> **Context Preservation Note:** When a rewrite loop is triggered, previous conversational history elements are intentionally dropped. This structural reset ensures that lower VRAM consumer cards (like an RTX 3060 12GB) do not overflow their context boundaries when handling deep agentic steps.

---

## Extending the Core to a "Claude-Style" Wrapper

To scale `AgentLoop` from a simple script validator into a more advanced, continuous autonomous assistant workspace, consider implementing these architectural patterns:

### 1. Contextual History Buffering
Currently, the loop drops memory to safeguard hardware parameters. To introduce state memory, replace the simple string format structure inside `call_llm` with a systematic structured message list container:
```python
# Transition from simple prompt combinations to standard payload tracking:
payload = {
    "model": self.model,
    "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ],
    "stream": False
}
```

### 2. Multi-Turn Tool Execution Hooks
To allow the agent to inspect files, execute code tests, or run compilation validations directly on your host environment, integrate schema-based tool registration before finishing the loop. You can catch specific structured markdown blocks (like ` ```bash ` blocks) returned by the writer, execute them inside a sandboxed subprocess execution layer, and feed the structural errors straight into the critic step dynamically.