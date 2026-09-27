from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from ai_scientist.research_os.agents import ActionRequest


CHANNEL_PRIORITY = ("api_cli", "http", "playwright", "desktop_ui", "vision")


class ActionBroker:
    def __init__(self, root: str | Path, *, handlers: dict[str, Callable], allowed_domains: set[str] | None = None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.handlers = handlers
        self.allowed_domains = allowed_domains or set()
        self.log_path = self.root / "actions.jsonl"
        self.completed: dict[str, dict[str, Any]] = {}
        if self.log_path.exists():
            for line in self.log_path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                self.completed[record["idempotency_key"]] = record["result"]

    def browser_session(self, action_id: str) -> dict[str, str]:
        session_root = self.root / "browser" / action_id
        profile = session_root / "profile"
        downloads = session_root / "downloads"
        profile.mkdir(parents=True, exist_ok=True)
        downloads.mkdir(parents=True, exist_ok=True)
        metadata = session_root / "session.json"
        metadata.write_text(json.dumps({"action_id": action_id, "isolated_profile": True}), encoding="utf-8")
        return {
            "profile_dir": str(profile), "trace": str(session_root / "trace.zip"),
            "screenshot": str(session_root / "screenshot.png"), "downloads": str(downloads), "metadata": str(metadata),
        }

    def execute(self, request: ActionRequest) -> dict[str, Any]:
        if request.idempotency_key in self.completed:
            return self.completed[request.idempotency_key]
        if request.domain and self.allowed_domains and request.domain not in self.allowed_domains:
            raise PermissionError(f"domain is not allowed: {request.domain}")
        if request.risk == "HIGH" and not request.approval_id:
            raise PermissionError("high-risk action requires explicit approval")
        channel = next((name for name in CHANNEL_PRIORITY if name in request.allowed_channels and name in self.handlers), None)
        if not channel:
            raise RuntimeError("no permitted action channel is available")
        session = self.browser_session(request.action_id) if channel == "playwright" else None
        result = self.handlers[channel](request, session)
        record = {"action_id": request.action_id, "idempotency_key": request.idempotency_key, "channel": channel, "result": result}
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.completed[request.idempotency_key] = result
        return result
