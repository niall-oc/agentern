import httpx
import json
import os
import asyncio
from agent.prompts import get_prompt
from vector.chroma import VectorStore

# =====================================================================
# USER-FACING MESSAGING CONFIGURATION
# Modify these strings to change how the agent talks to the user
# across both run_loop and stream_loop execution pipelines.
# =====================================================================
USER_MESSAGES = {
    "steps": {
        "triage": "## 1. Analyzing your request",
        "planning": "## 2. Planning the solution",
        "audit": "## 3. Reviewing the plan",
        "execute": "## 4. Working on the answer",
        "review": "## 5. Checking the final output"
    },
    "status": {
        "initializing": "[Searching your vector database for relevant context...]",
        "mode_code": "Task type identified: Software Engineering / Coding",
        "mode_text": "Task type identified: General Information / Text",
        "audit_ledger": "**Review findings:**",
        "plan_fix": "*The initial plan needs adjustments to match your request perfectly. Correcting it now...*",
        "plan_updated": "**Updated plan:**",
        "review_eval": "**Quality check results:**",
        "review_passed": "**Success:** The output passed all checks.",
        "review_fix": "*Fixing issues found during the quality check...*",
        "review_updated": "**Revised output:**",
        "final_output_header": "## Final Response"
    },
    "technical": {
        "engine_code": "Routed to Software Engineering Engine",
        "engine_text": "Routed to Content Generation Engine",
        "turn_label": "Attempt"
    }
}

class AgentLoop:
    def __init__(self, model="qwen2.5-coder"):
        self.llm_url = os.getenv("OLLAMA_URL", "http://172.17.0.1:11434/api/generate")
        self.model = model
        self.vector_store = VectorStore()

    async def call_llm(self, system: str, prompt: str) -> str:
        # Protects against <TransferEncodingError> dropouts with up to 3 retries
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=180.0) as client:
                    res = await client.post(self.llm_url, json={
                        "model": self.model,
                        "prompt": f"{system}\n\n{prompt}",
                        "stream": False
                    })
                    if res.status_code == 200:
                        return res.json().get("response", "").strip()
                    return f"Error: LLM returned status {res.status_code}"
            except (httpx.RemoteProtocolError, httpx.TransferError) as e:
                if attempt == 2:
                    return f"Error: Ollama connection dropped text chunks: {str(e)}"
                print(f"Connection dropped mid-transit. Retrying turn (Attempt {attempt + 1}/3)...")
                await asyncio.sleep(1)
            except Exception as e:
                return f"Error connecting to LLM: {str(e)}"
        return "Error: Failed to fetch generation after multiple retries."

    async def run_loop(self, task: str, on_step_cb=None) -> str:
        context = self.vector_store.search(task)
        
        # Step 1: Classify Task Modality
        modality = await self.call_llm(get_prompt("CLASSIFIER_PROMPT"), f"Task: {task}")
        is_code_task = "CODE" in modality.upper()
        if on_step_cb:
            msg = USER_MESSAGES["technical"]["engine_code"] if is_code_task else USER_MESSAGES["technical"]["engine_text"]
            await on_step_cb(USER_MESSAGES["steps"]["triage"], msg)

        # Step 2: Formulate Initial Plan
        plan = await self.call_llm(get_prompt("PLANNER_PROMPT"), f"Task: {task}\nContext: {context}")
        if on_step_cb:
            await on_step_cb(USER_MESSAGES["steps"]["planning"], plan)
            
        # Step 3: Plan Critique Audit Loop
        for p_idx in range(2):
            plan_audit = await self.call_llm(
                get_prompt("PLAN_CRITIQUE_PROMPT"), 
                f"Original Task: {task}\nProposed Plan: {plan}"
            )
            if on_step_cb:
                label = f"{USER_MESSAGES['steps']['audit']} ({USER_MESSAGES['technical']['turn_label']} {p_idx+1})"
                await on_step_cb(label, plan_audit)
                
            if "PLAN_PASS" in plan_audit.upper():
                break
                
            # Re-plan if plan auditor objects
            plan = await self.call_llm(
                get_prompt("PLANNER_PROMPT"), 
                f"Task: {task}\nContext: {context}\nFix Planning Flaws: {plan_audit}\nPrevious Plan: {plan}"
            )

        # Step 4: Execute Base Generation via Dynamic Routing
        exec_prompt = get_prompt("WRITER_PROMPT") if is_code_task else get_prompt("RESPONDER_PROMPT")
        output = await self.call_llm(exec_prompt, f"Task: {task}\nPlan: {plan}\nContext: {context}")
        if on_step_cb:
            await on_step_cb(USER_MESSAGES["steps"]["execute"], output)
        
        # Step 5: Final Execution Critique Loop
        max_retries = 2
        for i in range(max_retries):
            critique = await self.call_llm(get_prompt("CRITIQUE_PROMPT"), f"Task: {task}\nOutput: {output}")
            if on_step_cb:
                label = f"{USER_MESSAGES['steps']['review']} {i+1}"
                await on_step_cb(label, critique)

            if "PASS" in critique.upper():
                break
            
            output = await self.call_llm(
                exec_prompt, 
                f"Task: {task}\nFix issues: {critique}\nCurrent Version: {output}"
            )
            if on_step_cb:
                label = f"{USER_MESSAGES['status']['review_updated']} ({USER_MESSAGES['technical']['turn_label']} {i+1})"
                await on_step_cb(label, output)
            
        return output

    async def stream_loop(self, task: str):
        def make_sse(text):
            return f"data: {json.dumps({'choices': [{'delta': {'content': text}}]})}\n\n"

        yield make_sse("<think>\n")
        yield make_sse(f"{USER_MESSAGES['status']['initializing']}\n")
        
        # 1. Triage
        modality = await self.call_llm(get_prompt("CLASSIFIER_PROMPT"), f"Task: {task}")
        is_code_task = "CODE" in modality.upper()
        mode_str = USER_MESSAGES["status"]["mode_code"] if is_code_task else USER_MESSAGES["status"]["mode_text"]
        yield make_sse(f"{USER_MESSAGES['steps']['triage']}\n- {mode_str}\n\n---\n")

        context = self.vector_store.search(task)
        
        # 2. Plan Generation
        yield make_sse(f"{USER_MESSAGES['steps']['planning']}\n")
        plan = await self.call_llm(get_prompt("PLANNER_PROMPT"), f"Task: {task}\nContext: {context}")
        yield make_sse(f"{plan}\n\n---\n")
        
        # 3. Plan Verification
        yield make_sse(f"{USER_MESSAGES['steps']['audit']}\n")
        plan_audit = await self.call_llm(get_prompt("PLAN_CRITIQUE_PROMPT"), f"Original Task: {task}\nProposed Plan: {plan}")
        yield make_sse(f"{USER_MESSAGES['status']['audit_ledger']} {plan_audit}\n\n")
        
        if "PLAN_PASS" not in plan_audit.upper():
            yield make_sse(f"{USER_MESSAGES['status']['plan_fix']}\n")
            plan = await self.call_llm(get_prompt("PLANNER_PROMPT"), f"Task: {task}\nContext: {context}\nFix Flaws: {plan_audit}\nPrevious Plan: {plan}")
            yield make_sse(f"{USER_MESSAGES['status']['plan_updated']}\n{plan}\n\n")
        yield make_sse("---\n")

        # 4. Draft Generation Execution
        yield make_sse(f"{USER_MESSAGES['steps']['execute']}\n")
        exec_prompt = get_prompt("WRITER_PROMPT") if is_code_task else get_prompt("RESPONDER_PROMPT")
        output = await self.call_llm(exec_prompt, f"Task: {task}\nPlan: {plan}\nContext: {context}")
        yield make_sse(f"{output}\n\n---\n")
        
        # 5. Output Optimization Cycles
        max_retries = 2
        for i in range(max_retries):
            yield make_sse(f"## {USER_MESSAGES['steps']['review'].split('## ')[-1]} {i+1}\n")
            critique = await self.call_llm(get_prompt("CRITIQUE_PROMPT"), f"Task: {task}\nOutput: {output}")
            yield make_sse(f"{USER_MESSAGES['status']['review_eval']}\n{critique}\n\n")
            
            if "PASS" in critique.upper():
                yield make_sse(f"{USER_MESSAGES['status']['review_passed']}\n\n")
                break
                
            yield make_sse(f"{USER_MESSAGES['status']['review_fix']}\n")
            output = await self.call_llm(exec_prompt, f"Task: {task}\nFix issues: {critique}\nCurrent Version: {output}")
            yield make_sse(f"{USER_MESSAGES['status']['review_updated']}\n{output}\n\n")

        yield make_sse("</think>\n\n")
        yield make_sse(f"{USER_MESSAGES['status']['final_output_header']}\n")
        yield make_sse(output)
        yield "data: [DONE]\n\n"