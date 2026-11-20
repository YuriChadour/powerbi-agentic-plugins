"""Developer-session access to fab and az for apply: reads and idempotent writes (no secrets)."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ADO_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"


class StepError(SystemExit):
    """A failing apply step: one message naming the cause and the fix."""


class Ops:
    def _run(self, command: list[str]) -> subprocess.CompletedProcess:
        executable = shutil.which(command[0])
        if not executable:
            raise StepError(f"'{command[0]}' is not installed or not on PATH; install it and sign in as the developer")
        try:
            return subprocess.run([executable, *command[1:]], capture_output=True, text=True, timeout=15)
        except subprocess.TimeoutExpired as exc:
            raise StepError(f"{command[0]} command timed out after 15 seconds: {' '.join(command[1:3])}") from exc

    def fab_get(self, path: str):
        done = self._run(["fab", "api", path])
        if done.returncode:
            return None
        try:
            body = json.loads(done.stdout)
        except json.JSONDecodeError:
            return None
        return body.get("text") if body.get("status_code") == 200 else None

    def fab_post(self, path: str, body: dict) -> dict:
        done = self._run(["fab", "api", "-X", "post", path, "-i", json.dumps(body)])
        try:
            reply = json.loads(done.stdout)
        except json.JSONDecodeError:
            reply = {}
        status = reply.get("status_code")
        if done.returncode or status not in (200, 201, 202):
            raise StepError(f"POST {path} failed ({status or done.returncode}): {(done.stdout or done.stderr)[:300]}")
        return reply.get("text") or {}

    def az_json(self, *args: str):
        done = self._run(["az", *args, "--output", "json"])
        if done.returncode:
            return None
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:
            return None

    def ado_rest(self, method: str, url: str, body: dict | None = None):
        command = ["az", "rest", "--resource", ADO_RESOURCE, "--method", method, "--url", url]
        temp = None
        if body is not None:
            temp = Path(tempfile.mkdtemp()) / "body.json"
            temp.write_text(json.dumps(body), encoding="utf-8")
            command += ["--body", f"@{temp}", "--headers", "Content-Type=application/json"]
        done = self._run(command)
        if temp:
            shutil.rmtree(temp.parent, ignore_errors=True)
        if done.returncode:
            if method.lower() == "get":
                return None
            raise StepError(f"Azure DevOps {method} {url} failed: {done.stderr[:300]}")
        return json.loads(done.stdout) if done.stdout.strip() else {}

    def developer_object_id(self) -> str | None:
        done = self._run(["az", "ad", "signed-in-user", "show", "--query", "id", "--output", "tsv"])
        return done.stdout.strip() or None if done.returncode == 0 else None
