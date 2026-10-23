"""Safety hooks and command interception for Celesto sandbox execution."""
import os
import re
import json
from datetime import datetime, timezone
from typing import Dict, Any

COMMANDS_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "commands.jsonl")


class CommandBlockedError(Exception):
    """Raised when an untrusted command is blocked by the hypervisor safety policy."""
    pass


class SafetyHook:
    """Pre-execution hook inspecting commands before dispatching to Celesto guest."""
    
    FORBIDDEN_PATTERNS = [
        re.compile(r"curl.*attacker\.example\.com", re.IGNORECASE),
        re.compile(r"curl.*198\.51\.100\.", re.IGNORECASE),
        re.compile(r"rm\s+-rf\s+/(?!\w)", re.IGNORECASE),
        re.compile(r"cat\s+/etc/shadow", re.IGNORECASE),
        re.compile(r":\(\)\{.*:\&", re.IGNORECASE),
    ]

    @classmethod
    def inspect(cls, command: str) -> bool:
        """Inspect command. Returns True if allowed, False if blocked."""
        for pattern in cls.FORBIDDEN_PATTERNS:
            if pattern.search(command):
                return False
        return True


def audit_command_line(sandbox_name: str, command: str, decision: str) -> Dict[str, Any]:
    """Append verified command attempt to logs/commands.jsonl strictly targeting celesto_sandbox."""
    os.makedirs(os.path.dirname(COMMANDS_LOG_PATH), exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sandbox_name": sandbox_name,
        "command": command,
        "decision": decision,
        "execution_target": "celesto_sandbox"
    }
    with open(COMMANDS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
