"""Policy CLI: feed a boundary action through the engine, read the verdict.

Pure evaluation — no database writes. Facts come from the live tool
server unless `--facts` supplies them (hermetic mode). Backend + MCP
server must be up for live mode; INCEPTION key is not needed.

Usage:
  python scripts/policy_decide.py --contract contract.json --action action.json
  python scripts/policy_decide.py --contract contract.json --action action.json --facts facts.json

contract.json: {"task_id": ..., "goal": ..., "customer_id": ..., "order_id": ...,
  "ticket_id": ..., "effects": [{"effect": ..., "params": {...}, "capability": ...}],
  "capabilities": [...], "status": "ok"}
action.json: {"tool": "browser_submit", "params": {"effect": ..., ...}, "rationale": "..."}
facts.json: {"customer_id": ..., "order": {...}, "ticket": {...},
  "existing_replacement": null, "existing_refund": null, "refunds_last_90d": 0,
  "policies": {}, "missing": []}
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "common"))
sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate one action against policy.")
    parser.add_argument("--contract", required=True, help="Contract JSON file")
    parser.add_argument("--action", required=True, help="Action JSON file")
    parser.add_argument("--facts", default="", help="Facts JSON file (else live)")
    args = parser.parse_args()

    from agent.contract.models import Contract
    from agent.policy import authorization
    from agent.policy.facts import Facts, gather_facts

    contract = Contract.model_validate(json.loads(Path(args.contract).read_text(encoding="utf-8")))
    action = json.loads(Path(args.action).read_text(encoding="utf-8"))
    if args.facts:
        facts = Facts(**json.loads(Path(args.facts).read_text(encoding="utf-8")))
    else:
        from agent.adapters.mcp_gateway import MCPToolGateway

        mcp_url = os.environ.get("MCP_URL", "http://127.0.0.1:8002")
        gateway = MCPToolGateway(mcp_url)
        httpx.post(
            f"{mcp_url}/admin/tasks/{contract.task_id}/capabilities",
            json={"capabilities": ["read", "read.fallback", "probe", "browser"]},
            timeout=10,
        ).raise_for_status()
        facts = gather_facts(contract.task_id, contract, action, gateway)

    verdict = authorization.evaluate(contract, action, facts, date.today())
    print(f"outcome: {verdict.outcome}")
    print(f"rule: {verdict.rule_id}")
    print(f"reason: {verdict.reason}")
    if verdict.outcome == "allow" and action.get("tool") == "browser_submit":
        from agent.policy.issuer import issue_submit_token

        token = issue_submit_token(
            os.environ.get("POLICY_TOKEN_SECRET", "local-policy-secret"),
            contract.task_id,
            action.get("params", {}),
        )
        print(f"token: {token}")


if __name__ == "__main__":
    main()
