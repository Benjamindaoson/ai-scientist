from __future__ import annotations

import json
from pathlib import Path

import httpx

from ai_scientist.experiment.sandbox import WorkspaceSandbox
from ai_scientist.research_os.agents import ActionRequest


class CLIActionHandler:
    def __init__(self, sandbox: WorkspaceSandbox | None = None):
        self.sandbox = sandbox or WorkspaceSandbox()

    def __call__(self, request: ActionRequest, _session) -> dict:
        command = request.payload.get("command")
        workspace = request.payload.get("workspace")
        if not isinstance(command, list) or not workspace:
            raise ValueError("CLI action requires list command and workspace")
        completed = self.sandbox.run(command, workspace, request.payload.get("env", {}), int(request.payload.get("timeout", 300)))
        return {"return_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "artifact_refs": []}


class HTTPActionHandler:
    def __call__(self, request: ActionRequest, _session) -> dict:
        method = str(request.payload.get("method", "GET")).upper()
        response = httpx.request(method, request.target, params=request.payload.get("params"), json=request.payload.get("json"), timeout=30, follow_redirects=True)
        response.raise_for_status()
        return {"status_code": response.status_code, "url": str(response.url), "content": response.text, "artifact_refs": []}


class PlaywrightActionHandler:
    """Browser handler using a per-action persistent profile; it never opens the user's browser profile."""

    def __init__(self, headless: bool = True):
        self.headless = headless

    def __call__(self, request: ActionRequest, session: dict[str, str] | None) -> dict:
        if not session:
            raise ValueError("Playwright action requires an isolated session")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("install the browser extra to use Playwright actions") from exc
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                session["profile_dir"], headless=self.headless, accept_downloads=True,
            )
            context.tracing.start(screenshots=True, snapshots=True, sources=False)
            page = context.pages[0] if context.pages else context.new_page()
            response = page.goto(request.target, wait_until=request.payload.get("wait_until", "domcontentloaded"))
            page.screenshot(path=session["screenshot"], full_page=True)
            context.tracing.stop(path=session["trace"])
            result = {
                "status_code": response.status if response else None,
                "url": page.url,
                "title": page.title(),
                "content": page.content(),
                "artifact_refs": [session["trace"], session["screenshot"], session["metadata"]],
            }
            Path(session["metadata"]).write_text(json.dumps({"action_id": request.action_id, "url": page.url, "isolated_profile": True}, indent=2), encoding="utf-8")
            context.close()
            return result
