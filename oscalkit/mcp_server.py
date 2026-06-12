"""oscalkit MCP server — stdio JSON-RPC 2.0. Standard library only.

    {"command": "python", "args": ["-m", "oscalkit", "mcp"]}
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

from oscalkit import TOOL_NAME, TOOL_VERSION
from oscalkit.core import (
    OscalError,
    control_ids,
    coverage,
    load,
    validate,
)

PROTOCOL_VERSION = "2024-11-05"

_TOOLS = [
    {
        "name": "validate",
        "description": "Validate an OSCAL document (catalog/profile/"
                       "component-definition/SSP) for structure and references.",
        "inputSchema": {
            "type": "object",
            "properties": {"file": {"type": "string"}},
            "required": ["file"], "additionalProperties": False,
        },
    },
    {
        "name": "controls",
        "description": "List the control ids an OSCAL document covers.",
        "inputSchema": {
            "type": "object",
            "properties": {"file": {"type": "string"}},
            "required": ["file"], "additionalProperties": False,
        },
    },
    {
        "name": "coverage",
        "description": "Diff the controls a component/SSP claims against a "
                       "baseline; reports covered, missing, and extra controls.",
        "inputSchema": {
            "type": "object",
            "properties": {"claimed": {"type": "string"},
                           "baseline": {"type": "string"}},
            "required": ["claimed", "baseline"], "additionalProperties": False,
        },
    },
]


def _result(req_id, result): return {"jsonrpc": "2.0", "id": req_id, "result": result}
def _error(req_id, code, msg): return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": msg}}


def _call_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "validate":
        f = args.get("file")
        if not isinstance(f, str) or not f:
            raise ValueError("`file` (string) is required")
        res = validate(load(f), source=f).to_dict()
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}],
                "isError": not res["ok"]}
    if name == "controls":
        f = args.get("file")
        if not isinstance(f, str) or not f:
            raise ValueError("`file` (string) is required")
        ids = control_ids(load(f))
        return {"content": [{"type": "text",
                             "text": json.dumps({"controls": ids, "count": len(ids)},
                                                indent=2)}], "isError": False}
    if name == "coverage":
        claimed, baseline = args.get("claimed"), args.get("baseline")
        if not isinstance(claimed, str) or not isinstance(baseline, str):
            raise ValueError("`claimed` and `baseline` (strings) are required")
        cov = coverage(load(claimed), load(baseline))
        return {"content": [{"type": "text", "text": json.dumps(cov, indent=2)}],
                "isError": False}
    raise ValueError(f"unknown tool: {name}")


def handle_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}
    is_notification = "id" not in req

    if method == "initialize":
        res = _result(req_id, {"protocolVersion": PROTOCOL_VERSION,
                               "capabilities": {"tools": {"listChanged": False}},
                               "serverInfo": {"name": TOOL_NAME, "version": TOOL_VERSION}})
        return None if is_notification else res
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "ping":
        return None if is_notification else _result(req_id, {})
    if method == "tools/list":
        return _result(req_id, {"tools": _TOOLS})
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            return _result(req_id, _call_tool(name, args))
        except (ValueError, OSError, OscalError) as exc:
            return _error(req_id, -32602, str(exc))
        except Exception as exc:  # pragma: no cover
            return _error(req_id, -32603, f"internal error: {exc}")
    if is_notification:
        return None
    return _error(req_id, -32601, f"method not found: {method}")


def run_mcp_server(stdin=None, stdout=None) -> None:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            stdout.write(json.dumps(_error(None, -32700, "parse error")) + "\n")
            stdout.flush()
            continue
        response = handle_request(req)
        if response is not None:
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()


if __name__ == "__main__":
    run_mcp_server()
