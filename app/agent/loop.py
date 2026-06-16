import httpx
import json
import os
import asyncio
from typing import AsyncGenerator, Optional
from vector.chroma import VectorStore


class AgentLoop:
    def __init__(self, model, agent_config, vector_search=False):
        self.llm_url = os.getenv("OLLAMA_URL", "http://172.17.0.1:11434/api/generate")
        self.model = model
        self.agent_config = agent_config
        self.vector_search = vector_search
        self.vector_store = VectorStore()

    async def call_llm(self, system: str, prompt: str) -> str:
        # Protects against <TransferEncodingError> dropouts with up to 3 retries
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=180.0) as client:
                    res = await client.post(
                        self.llm_url,
                        json={
                            "model": self.model,
                            "prompt": f"{system}\n\n{prompt}",
                            "stream": False,
                        },
                    )
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

    def _build_classifier_prompt(self) -> str:
        channels = self.agent_config["EXECUTION_CHANNELS"]
        base_prompt = channels["prompt"].strip()
        
        options_str = ""
        for route_key, route_data in channels["routes"].items():
            options_str += f"- {route_key}: {route_data['description']}\n"
            
        options_str += "Output exactly one keyword option. Do not include any formatting, markdown, or introductory text."
        
        return f"{base_prompt}\n\n{options_str}"

    def _get_route_config(self, modality_raw: str) -> dict:
        routes = self.agent_config["EXECUTION_CHANNELS"]["routes"]
        modality = modality_raw.strip().upper()
        
        # Exact match
        if modality in routes:
            return routes[modality], modality
            
        # Fallback heuristic if LLM output includes formatting
        for route_key in routes.keys():
            if route_key in modality:
                return routes[route_key], route_key
                
        # Default fallback
        fallback_key = list(routes.keys())[0]
        return routes[fallback_key], fallback_key

    # ------------------------------------------------------------------
    # Shared pipeline: an async generator that yields (label, content)
    # tuples progressively.  Both run_loop and stream_loop iterate over
    # it with 'async for' and handle each notification in their own way.
    # ------------------------------------------------------------------
    async def _execute_pipeline(
        self,
        task: str,
        context: str,
        route_config: dict,
        route_key: str,
    ) -> AsyncGenerator[tuple[str, str], None]:

        yield (
            route_config['description'],
            f"Task type identified: {route_key.replace('_', ' ').title()}",
        )

        artifacts = {
            "task": task,
            "context": context,
        }

        stages = route_config.get("stages", {})

        for stage_name, stage_cfg in stages.items():

            prompt = stage_cfg["prompt"]
            critique_prompt = stage_cfg.get("critique")
            max_turns = stage_cfg.get("max_refinement_turns", 0)

            yield (
                f"{stage_name}", "one moment..."
            )

            stage_input = f"""
            Task:
            {task}

            Context:
            {context}

            Previous Outputs:
            {self._format_artifacts(artifacts)}
            """

            output = await self.call_llm(prompt, stage_input)

            yield (
                f"{stage_name}_output",
                output,
            )

            for turn in range(max_turns):

                if not critique_prompt:
                    break

                critique_input = f"""
                Task:
                {task}

                Stage:
                {stage_name}

                Output:
                {output}
                """

                critique = await self.call_llm(
                    critique_prompt,
                    critique_input,
                )

                yield (
                    f"{stage_name}_review_{turn + 1}",
                    critique,
                )

                critique_upper = critique.upper()

                if (
                    "PASS" in critique_upper
                    or "PLAN_PASS" in critique_upper
                ):
                    break

                revision_input = f"""
                Task:
                {task}

                Context:
                {context}

                Current Output:
                {output}

                Required Corrections:
                {critique}
                """

                output = await self.call_llm(
                    prompt,
                    revision_input,
                )

                yield (
                    f"{stage_name}_revision_{turn + 1}",
                    output,
                )

            artifacts[stage_name] = output
            artifacts["latest"] = output

        yield ("__FINAL__", artifacts["latest"])
    
    def _format_artifacts(self, artifacts: dict) -> str:
        """Format the artifacts into a single string."""
        sections = []

        for key, value in artifacts.items():

            if key in ("task", "context", "latest"):
                continue

            sections.append(f"=== {key.upper()} ===\n{value}\n")

        return "\n".join(sections)

    async def run_loop(self, task: str, on_step_cb=None) -> str:
        # 1. Retrieve context & classify modality
        context =""
        if self.vector_search:
            context = self.vector_store.search(task)
        classifier_system_prompt = self._build_classifier_prompt()
        modality_raw = await self.call_llm(classifier_system_prompt, f"Task: {task}")
        route_config, route_key = self._get_route_config(modality_raw)

        # 2. Run the shared pipeline -- iterate progressively and forward
        #    each notification to the callback.
        final_output: str = ""
        async for label, content in self._execute_pipeline(
            task, context, route_config, route_key
        ):
            if label == "__FINAL__":
                final_output = content
            elif on_step_cb:
                await on_step_cb(label, content)

        return final_output

    async def stream_loop(self, task: str):
        def make_sse(text: str) -> str:
            return f"data: {json.dumps({'choices': [{'delta': {'content': text}}]})}\n\n"

        yield make_sse("<think>\n")

        # 1. Retrieve context & classify modality
        context =""
        if self.vector_search:
            context = self.vector_store.search(task)
        classifier_system_prompt = self._build_classifier_prompt()
        modality_raw = await self.call_llm(classifier_system_prompt, f"Task: {task}")
        route_config, route_key = self._get_route_config(modality_raw)

        # 2. Run the shared pipeline -- convert each notification to SSE
        #    frames *as it arrives*, yielding them progressively.
        final_output: str = ""
        async for label, content in self._execute_pipeline(
            task, context, route_config, route_key
        ):
            if label == "__FINAL__":
                final_output = content
        
            yield make_sse(f"{label}\n- {content}\n\n---\n")
            
        yield make_sse("</think>\n\n")
        yield make_sse(final_output)
        yield "data: [DONE]\n\n"