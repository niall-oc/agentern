# Tuning Agent Behavior via `prompts.yaml`

The cognitive behavior, style constraints, and logical approach of **Agentern** are driven completely outside of the core application code. The system utilizes `app/prompts.yaml` to define individual system instructions for the different execution stages.

---

## The Prompt Lifecycle

When `AgentLoop` processes a request, it invokes `get_prompt()` dynamically for each step of the lifecycle. The strings in `prompts.yaml` use standard YAML block scalars (`|`) to maintain clean, multi-line structural instructions without interfering with Python string templates.

```yaml
PLANNER_PROMPT: |
  You are the Agentern Planner. 
  Analyze the user's request and create a concise, step-by-step execution plan.
  Do not write the final code. Only outline the logical steps required to solve the problem.

WRITER_PROMPT: |
  You are the Agentern Writer. 
  Your job is to execute the provided Plan using the provided Context.
  Write the complete, functional code to satisfy the user's request.

CRITIQUE_PROMPT: |
  You are the Agentern Critic.
  Review the Generated Code against the Original Request. 
  If the code fails to meet the requirements, identify the bugs or missing features.
  If the code is flawless and ready, output "PASS" along with your final approval.
```

---

## Modifying Stage Behavior

Because these prompts are injected directly as the `system` parameter into `call_llm(system, prompt)`, you can completely alter how the underlying model behaves by tuning the definitions.

### 1. Hardening the Critic (Reducing Silent Failures)
If your 7B/9B model is passing buggy code too early, make the `CRITIQUE_PROMPT` more hostile. 
*   *Adjustment:* Explicitly instruct the critic to look for edge cases, missing imports, unhandled exceptions, or off-by-one errors before granting a `PASS`.

### 2. Standardizing Code Generation
If the generated code lacks structural consistency (e.g., missing type annotations or poor documentation):
*   *Adjustment:* Modify `WRITER_PROMPT` to include strict formatting constraints, such as: *"Always include Python type hints for arguments and return values, and wrap code in clear execution blocks."*

---

## Applying Changes Real-Time

When running Agentern via Docker Compose, you do not need to rewrite your Python application to experiment with new prompt strategies. 

1. Edit `app/prompts.yaml`.
2. Restart the backend container to reload the YAML configuration into memory:
```bash
   docker compose restart agentern
   ```
3. Monitor your active container output or frontend client logs to verify how the model handles the adjusted boundaries.