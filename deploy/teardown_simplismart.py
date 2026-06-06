"""Delete the Simplismart deployment and model repo to stop GPU billing."""

from __future__ import annotations
import os, sys
from dotenv import load_dotenv, set_key
from pathlib import Path

load_dotenv()
ENV_PATH = Path(__file__).parent.parent / ".env"


def main() -> None:
    from simplismart import Simplismart

    client = Simplismart(pg_token=os.environ["SIMPLISMART_API_KEY"])

    deployment_id = os.environ.get("SIMPLISMART_DEPLOYMENT_ID", "").strip()
    if not deployment_id:
        print("[Simplismart] SIMPLISMART_DEPLOYMENT_ID not set in .env")
        deployment_id = input("Enter deployment ID to delete: ").strip()

    if not deployment_id:
        print("[Simplismart] No deployment ID provided. Exiting.")
        sys.exit(1)

    print(f"[Simplismart] Deleting deployment {deployment_id}...")
    try:
        result = client.delete_deployment(deployment_id, org_id=os.environ.get("SIMPLISMART_ORG_ID"))
        print(f"[Simplismart] Deployment deleted: {result}")
        set_key(str(ENV_PATH), "SIMPLISMART_DEPLOYMENT_ID", "")
        set_key(str(ENV_PATH), "SIMPLISMART_BASE_URL", "")
    except Exception as e:
        print(f"[Simplismart] Delete failed: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
