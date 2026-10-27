"""
Pipeline callback handler — logs every agent step to console and provides
an audit trail that can be inspected after each run.
"""

from langchain_core.callbacks.base import BaseCallbackHandler
from datetime import datetime


class PipelineCallbackHandler(BaseCallbackHandler):
    """
    Attached to every agent. Logs:
      - Agent start / end
      - Tool calls (simulation engine, BLAST, etc.)
      - LLM calls (model name, token usage)
      - Errors and retries
    """

    def __init__(self, run_id: str, verbose: bool = True):
        self.run_id  = run_id
        self.verbose = verbose
        self.log: list = []

    def _log(self, event: str, detail: str = ""):
        ts  = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        msg = f"[{ts}] [{self.run_id}] {event}"
        if detail:
            msg += f" | {detail[:120]}"
        self.log.append(msg)
        if self.verbose:
            print(msg)

    def on_agent_action(self, action, **kwargs):
        self._log("🔧 TOOL CALL", f"{action.tool}({action.tool_input})")

    def on_agent_finish(self, finish, **kwargs):
        self._log("✅ AGENT DONE", str(finish.return_values)[:80])

    def on_llm_start(self, serialized, prompts, **kwargs):
        self._log("🤖 LLM START", f"model={serialized.get('name', '?')}")

    def on_llm_end(self, response, **kwargs):
        tokens = getattr(response, "llm_output", {}).get("token_usage", {})
        self._log("🤖 LLM END", f"tokens={tokens}")

    def on_chain_start(self, serialized, inputs, **kwargs):
        self._log("⛓  CHAIN START", serialized.get("name", "?"))

    def on_chain_end(self, outputs, **kwargs):
        self._log("⛓  CHAIN END")

    def on_tool_error(self, error, **kwargs):
        self._log("❌ TOOL ERROR", str(error))

    def on_chain_error(self, error, **kwargs):
        self._log("❌ CHAIN ERROR", str(error))
