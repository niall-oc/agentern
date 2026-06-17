"""
Agent loop — inference orchestration for the agent.

Provides the :class:`AgentLoop` class which governs the multi-stage
pipeline that classifies a user task, routes it to the correct
execution channel, then runs a configurable chain of stages
(planning, writing, review, etc.) with optional critique-and-revision
refinement loops.

Two public entry points are available:

* :meth:`AgentLoop.run_loop` — a coroutine that returns the final
  output string and optionally calls an *on_step_cb* callback for
  each progress notification.
* :meth:`AgentLoop.stream_loop` — an async generator that yields
  `Server-Sent Events (SSE) <https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events>`_
  frames, allowing clients to stream progress in real time.

Both entry points share the same core logic via
:meth:`AgentLoop._execute_pipeline`, an async generator that yields
``(label, content)`` tuples progressively.
"""

import httpx
import json
import os
import asyncio
from typing import AsyncGenerator, Optional

from vector  import VectorStore


class AgentLoop:
    """Orchestrates the agent's multi-stage execution pipeline.

    The pipeline consists of these phases:

    1. **Classification** — determines the task modality and selects
       the appropriate execution route from the agent configuration.
    2. **Stage execution** — iterates through the route's configured
       stages, running LLM prompts and optional critique-and-revision
       loops for each stage.
    3. **Final output** — returns the latest generated artifact.

    Both :meth:`run_loop` and :meth:`stream_loop` follow the same
    sequence; the only difference is how progress notifications are
    delivered (callback vs. SSE).

    :param model: Name of the Ollama model to use (e.g. ``"qwen2.5-coder"``).
    :param agent_config: Dictionary loaded from the agent YAML
        configuration. Must contain an ``"EXECUTION_CHANNELS"`` key.
    :ollama_url: Base URL of the Ollama instance (e.g.
        ``"http://172.17.0.1:11434"``).  Used to send inference requests.
    :param vector_search: If ``True``, the agent will query the vector
        store for relevant context before executing the pipeline.
    """

    def __init__(self, model: str, agent_config: str, ollama_url: str, db_path: str = None):
        self.llm_url = ollama_url
        self.model = model
        self.agent_config = agent_config
        self.vector_store = None
        if isinstance(db_path, str) and db_path.strip():
            self.vector_store = VectorStore(db_path)

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def call_llm(self, system: str, prompt: str) -> str:
        """Send a prompt to the Ollama LLM and return the response.

        Implements automatic retry (up to 3 attempts) to guard against
        transient :class:`httpx.RemoteProtocolError` /
        :class:`httpx.TransferError` failures.

        :param system: The system-level instruction for the LLM.
        :param prompt: The user prompt to send.
        :returns: The LLM's response text, or an error string prefixed
            with ``"Error:"`` if all retries are exhausted.
        """
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=180.0) as client:
                    res = await client.post(
                        f"{self.llm_url.rstrip('/')}/api/generate",
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
                    return (
                        f"Error: Ollama connection dropped text chunks: {str(e)}"
                    )
                print(
                    f"Connection dropped mid-transit. "
                    f"Retrying turn (Attempt {attempt + 1}/3)..."
                )
                await asyncio.sleep(1)
            except Exception as e:
                return f"Error connecting to LLM: {str(e)}"
        return "Error: Failed to fetch generation after multiple retries."

    # ------------------------------------------------------------------
    # Modality classification helpers
    # ------------------------------------------------------------------

    def _build_classifier_prompt(self) -> str:
        """Build the system prompt used to classify the user's task.

        Reads the ``EXECUTION_CHANNELS`` section of the agent config
        and formats every available route as an option the LLM can
        choose from.

        :returns: A classifier system prompt string.
        """
        channels = self.agent_config["EXECUTION_CHANNELS"]
        base_prompt = channels["prompt"].strip()
        
        options_str = ""
        for route_key, route_data in channels["routes"].items():
            options_str += f"- {route_key}: {route_data['description']}\n"
        
        options_str += (
            "Output exactly one keyword option. "
            "Do not include any formatting, markdown, or introductory text."
        )

        return f"{base_prompt}\n\n{options_str}"

    def _get_route_config(self, modality_raw: str):
        """Resolve the raw LLM classifer output to a route configuration.

        Tries an exact match first, then falls back to substring
        matching, and finally returns the first available route if
        nothing else works.

        :param modality_raw: The raw output from the classifier LLM.
        :returns: A tuple ``(route_config_dict, route_key_string)``.
        """
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
    # Shared pipeline — async generator
    # ------------------------------------------------------------------

    async def _execute_pipeline(
        self,
        task: str,
        context: str,
        route_config: dict,
        route_key: str,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Execute the agent's configured stage pipeline.

        This is the core shared logic used by both :meth:`run_loop` and
        :meth:`stream_loop`.  It is an **async generator** that yields
        ``(label, content)`` tuples progressively as each stage and
        each critique/revision sub-step completes.  The final output is
        yielded with the special label ``"__FINAL__"``.

        **Stage lifecycle**

        For each stage defined in ``route_config["stages"]``:

        1. Yield ``(stage_name, "one moment...")`` as a header.
        2. Build the stage input from the task, context, and any
           artifacts produced by earlier stages.
        3. Call :meth:`call_llm` with the stage's prompt.
        4. Yield ``(f"{stage_name}_output", output)``.
        5. If the stage has a ``critique`` prompt and
           ``max_refinement_turns > 0``, enter a refinement loop:

           a. Call the critique prompt.
           b. Yield ``(f"{stage_name}_review_{turn}", critique)``.
           c. If ``"PASS"`` or ``"PLAN_PASS"`` appears in the critique,
              exit the loop early.
           d. Otherwise, call the stage prompt again with the critique
              as a correction instruction, then yield
              ``(f"{stage_name}_revision_{turn}", revised_output)``.
        6. Store the stage's output in the artifact dict for use by
           subsequent stages.

        :param task: The original user task string.
        :param context: Retrieved context from the vector store (empty
            string if vector search is disabled).
        :param route_config: The configuration dictionary for the
            selected execution route.
        :param route_key: The string key of the selected route.
        :yields: ``(label, content)`` tuples at each stage and
            sub-step.
        """
        yield (
            route_config["description"],
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

            yield (f"{stage_name}", "one moment...")

            stage_input = f"""
            Task:
            {task}

            Context:
            {context}

            Previous Outputs:
            {self._format_artifacts(artifacts)}
            """

            output = await self.call_llm(prompt, stage_input)

            yield (f"{stage_name}_output", output)

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

                yield (f"{stage_name}_review_{turn + 1}", critique)

                critique_upper = critique.upper()

                if "PASS" in critique_upper or "PLAN_PASS" in critique_upper:
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

                yield (f"{stage_name}_revision_{turn + 1}", output)

            artifacts[stage_name] = output
            artifacts["latest"] = output

        yield ("__FINAL__", artifacts["latest"])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_artifacts(artifacts: dict) -> str:
        """Format the artifact dict into a single string for prompt context.

        Skips the ``"task"``, ``"context"``, and ``"latest"`` keys
        (which are injected separately) and formats the remaining
        entries as ``=== STAGE_NAME ===\\ncontent\\n`` blocks.

        :param artifacts: The artifact dictionary produced during
            pipeline execution.
        :returns: A formatted string suitable for insertion into an
            LLM prompt.
        """
        sections = []

        for key, value in artifacts.items():
            if key in ("task", "context", "latest"):
                continue
            sections.append(f"=== {key.upper()} ===\n{value}\n")

        return "\n".join(sections)
    
    def _get_context(self, task: str):
        """
        Retrieve the context string for the given task.
        """
        if self.vector_store is not None:
            return self.vector_store.search(task)
        return ""

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def run_loop(self, task: str) -> str:
        """Run the full agent pipeline and return the final output.

        This is the **non-streaming** entry point.  Progress
        notifications are delivered to the optional *on_step_cb*
        callback.

        Usage::

            agent = AgentLoop(model, config)
            result = await agent.run_loop("Write a unit test for foo")

        :param task: The user's task string.
        :param on_step_cb: An optional async callback ``(label, content)``
            that will be awaited for each progress notification.  Can be
            ``None``.
        :returns: The final output string with the full reasoning trace
            prepended inside ``<reasoning>`` tags.
        """
        classifier_system_prompt = self._build_classifier_prompt()
        modality_raw = await self.call_llm(
            classifier_system_prompt, f"Task: {task}"
        )
        route_config, route_key = self._get_route_config(modality_raw)

        # Collect the full reasoning trace from all pipeline stages
        thought_trace = [f"Classification: {modality_raw}"]
        final_output: str = ""
        async for label, content in self._execute_pipeline(
            task, self._get_context(task), route_config, route_key
        ):
            if label == "__FINAL__":
                final_output = content
            else:
                thought_trace.append(f"=== {label} ===\n{content}")

        
        if thought_trace:
            final_output = f"<reasoning>\n{thought_trace}\n</reasoning>\n\n{final_output}"

        return final_output

    async def stream_loop(self, task: str):
        """Run the full agent pipeline and yield SSE frames.

        This is the **streaming** entry point, suitable for
        Server-Sent Events or similar real-time protocols.  Each step
        of the pipeline is yielded as an SSE ``data:`` frame
        immediately when it becomes available.

        Usage::

            agent = AgentLoop(model, config)
            async for frame in agent.stream_loop("Explain recursion"):
                await websocket.send(frame)

        :param task: The user's task string.
        :yields: SSE-formatted ``data:`` strings, one per notification.
            The final frame is ``"data: [DONE]\\n\\n"``.
        """
        def make_sse(text: str) -> str:
            return (
                f"data: {json.dumps({'choices': [{'delta': {'content': text}}]})}"
                f"\n\n"
            )

        yield make_sse("<think>\n")

        classifier_system_prompt = self._build_classifier_prompt()
        modality_raw = await self.call_llm(
            classifier_system_prompt, f"Task: {task}"
        )
        route_config, route_key = self._get_route_config(modality_raw)

        # 2. Run the shared pipeline -- convert each notification to SSE
        #    frames *as it arrives*, yielding them progressively.
        final_output: str = ""
        async for label, content in self._execute_pipeline(
            task, self._get_context(task), route_config, route_key
        ):
            if label == "__FINAL__":
                final_output = content
            else:
                yield make_sse(f"{label}\n- {content}\n\n---\n")
        
            yield make_sse(f"{label}\n- {content}\n\n---\n")
            
        yield make_sse("</think>\n\n")
        yield make_sse(final_output)
        yield "data: [DONE]\n\n"