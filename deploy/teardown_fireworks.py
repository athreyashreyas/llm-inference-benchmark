"""Delete the Fireworks deployment to stop GPU billing."""

from __future__ import annotations
import os, sys
import requests
from dotenv import load_dotenv, set_key
from pathlib import Path
load_dotenv()
ENV_PATH = Path(__file__).parent.parent / ".env"

def main() -> None:
    account_id    = os.environ["FIREWORKS_ACCOUNT_ID"]
    api_key       = os.environ["FIREWORKS_API_KEY"]
    deployment_id = os.environ.get("FIREWORKS_DEPLOYMENT_ID", "")

    if not deployment_id:
        deployment_id = input("Enter Fireworks deployment ID to delete: ").strip()
    if not deployment_id:
        print("[Fireworks] No deployment ID provided. Exiting.")
        sys.exit(0)

    # ignore_checks=true bypasses the "recent inference requests" guard
    url = f"https://api.fireworks.ai/v1/accounts/{account_id}/deployments/{deployment_id}?ignoreChecks=true"
    resp = requests.delete(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
    print(f"[Fireworks] DELETE → {resp.status_code}: {resp.text[:200]}")
    if resp.status_code in (200, 204):
        print("[Fireworks] Deployment deleted. GPU billing stopped.")
        set_key(str(ENV_PATH), "FIREWORKS_DEPLOYMENT_ID", "")
        set_key(str(ENV_PATH), "FIREWORKS_MODEL_ID", "")
    else:
        print("[Fireworks] Delete may have failed — check Fireworks dashboard.")

if __name__ == "__main__":
    main()
