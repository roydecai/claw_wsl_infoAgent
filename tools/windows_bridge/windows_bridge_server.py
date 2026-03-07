#!/usr/bin/env python
import json
import os
import re
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def _env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _allowed_prefixes() -> list[str]:
    raw = os.getenv("WINDOWS_BRIDGE_ALLOWED_PREFIXES", "").strip()
    if raw:
        return [p.strip() for p in raw.split(",") if p.strip()]
    return [
        "Get-",
        "Set-Location",
        "Test-Path",
        "Resolve-Path",
        "ls",
        "dir",
        "pwd",
        "echo",
        "whoami",
        "ipconfig",
        "tasklist",
        "systeminfo",
        "wt",
        "cmd /c",
        "powershell -NoProfile -Command",
    ]


DENY_PATTERNS = [
    re.compile(r"(?i)\brm\s+-rf\b"),
    re.compile(r"(?i)\bdel\s+\/[sqf]\b"),
    re.compile(r"(?i)\bformat\s+[a-z]:\b"),
    re.compile(r"(?i)\bshutdown\b"),
    re.compile(r"(?i)\brestart-computer\b"),
    re.compile(r"(?i)\bstop-computer\b"),
    re.compile(r"(?i)\bremove-item\b.+\b-recurse\b"),
    re.compile(r"(?i)\binvoke-expression\b"),
    re.compile(r"(?i)\biex\b"),
    re.compile(r"(?i)\bcurl\b.+\|"),
]


def command_allowed(command: str, prefixes: list[str]) -> bool:
    cmd = command.strip()
    if not cmd:
        return False
    for pattern in DENY_PATTERNS:
        if pattern.search(cmd):
            return False
    return any(cmd.lower().startswith(prefix.lower()) for prefix in prefixes)


def run_shell(command: str, timeout_seconds: int, prefixes: list[str]) -> tuple[int, dict]:
    if not command_allowed(command, prefixes):
        return 403, {"ok": False, "error": "Command is not allowed by bridge policy."}

    try:
        proc = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 408, {"ok": False, "error": "Command timed out."}

    return 200, {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def run_ui(action: str, text: str) -> tuple[int, dict]:
    if action == "launch_windows_terminal":
        subprocess.Popen(["wt.exe"])
        return 200, {"ok": True, "action": action, "message": "Windows Terminal launched."}

    if action == "open_notepad_and_type":
        ps_script = r'''
$ErrorActionPreference = "Stop"
function Escape-SendKeysText {
    param([string]$InputText)
    if ($null -eq $InputText) { return "" }
    $escaped = $InputText.Replace("{", "{{}").Replace("}", "{}}")
    $escaped = $escaped.Replace("+", "{+}").Replace("^", "{^}").Replace("%", "{%}")
    $escaped = $escaped.Replace("~", "{~}").Replace("(", "{(}").Replace(")", "{)}")
    $escaped = $escaped.Replace("[", "{[}").Replace("]", "{]}")
    return $escaped
}

$wshell = New-Object -ComObject WScript.Shell
Start-Process "notepad.exe" | Out-Null
Start-Sleep -Milliseconds 900
if (-not ($wshell.AppActivate("Notepad") -or $wshell.AppActivate("记事本"))) {
    throw "Notepad window could not be activated."
}
Start-Sleep -Milliseconds 250
$payload = Escape-SendKeysText -InputText $env:BRIDGE_UI_TEXT
$wshell.SendKeys($payload)
'''
        env = os.environ.copy()
        env["BRIDGE_UI_TEXT"] = text
        proc = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps_script,
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if proc.returncode != 0:
            return 500, {
                "ok": False,
                "error": "UI action failed.",
                "stderr": proc.stderr,
                "stdout": proc.stdout,
            }
        return 200, {"ok": True, "action": action, "message": "Notepad opened and text sent."}

    return 400, {
        "ok": False,
        "error": "Unsupported ui action.",
        "supported_actions": ["open_notepad_and_type", "launch_windows_terminal"],
    }


class BridgeHandler(BaseHTTPRequestHandler):
    token = ""
    prefixes: list[str] = []
    log_path = Path("windows_bridge.log")

    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _log_request(self, status: int, raw_body: str) -> None:
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{self.command}\t{self.path}\t{status}\t{raw_body}\n"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line)

    def do_GET(self) -> None:
        raw_body = ""
        if self.path != "/health":
            self._write_json(404, {"ok": False, "error": "Route not found."})
            self._log_request(404, raw_body)
            return
        payload = {"ok": True, "status": "healthy", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
        self._write_json(200, payload)
        self._log_request(200, raw_body)

    def do_POST(self) -> None:
        raw_body = ""
        if self.path != "/run":
            self._write_json(404, {"ok": False, "error": "Route not found."})
            self._log_request(404, raw_body)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""

        try:
            body = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            self._write_json(400, {"ok": False, "error": "Invalid JSON."})
            self._log_request(400, raw_body)
            return

        if body.get("token") != self.token:
            self._write_json(401, {"ok": False, "error": "Unauthorized."})
            self._log_request(401, raw_body)
            return

        req_type = str(body.get("type", "")).strip()
        if req_type == "shell":
            timeout = int(body.get("timeout_seconds", 30) or 30)
            status, payload = run_shell(str(body.get("cmd", "")), timeout, self.prefixes)
            self._write_json(status, payload)
            self._log_request(status, raw_body)
            return

        if req_type == "ui":
            status, payload = run_ui(str(body.get("action", "")), str(body.get("text", "")))
            self._write_json(status, payload)
            self._log_request(status, raw_body)
            return

        self._write_json(400, {
            "ok": False,
            "error": "Unsupported request type.",
            "supported_types": ["shell", "ui"],
        })
        self._log_request(400, raw_body)

    def log_message(self, _format: str, *_args) -> None:
        return


def main() -> None:
    token = _env_required("WINDOWS_BRIDGE_TOKEN")
    host = os.getenv("WINDOWS_BRIDGE_BIND_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("WINDOWS_BRIDGE_PORT", "8765"))
    log_path = Path(os.getenv("WINDOWS_BRIDGE_LOG_PATH", "").strip() or (Path(__file__).resolve().parent / "windows_bridge.log"))
    prefixes = _allowed_prefixes()

    BridgeHandler.token = token
    BridgeHandler.prefixes = prefixes
    BridgeHandler.log_path = log_path

    server = ThreadingHTTPServer((host, port), BridgeHandler)
    print(f"Windows bridge listening on http://{host}:{port}/")
    print(f"Log file: {log_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

