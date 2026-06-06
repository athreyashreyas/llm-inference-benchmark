"""
Simplismart dedicated deployment script for Gemma 3 4B Instruct.

Flow (per official quickstart):
  1. Compile model from HuggingFace onto Simplismart infrastructure
     - Skipped if SIMPLISMART_MODEL_REPO_UUID is set in .env (already compiled)
     - Skipped if a compiled repo named DEPLOYMENT_NAME already exists in SUCCESS state
  2. Poll until compilation status == SUCCESS
  3. Create dedicated deployment from compiled model repo
  4. Poll until deployment is healthy
  5. Write inference endpoint URL and IDs to .env

Usage:
  python deploy/deploy_simplismart.py             # full flow
  python deploy/deploy_simplismart.py --deploy-only  # skip compile, use UUID from .env

Compile time: ~20-60 min depending on model size and GPU availability.
GPU billing starts at deployment creation, stops when scale-to-zero kicks in.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv, set_key

load_dotenv()

ENV_PATH = Path(__file__).parent.parent / ".env"

SIMPLISMART_API_KEY      = os.environ.get("SIMPLISMART_API_KEY", "")
SIMPLISMART_ORG_ID       = os.environ.get("SIMPLISMART_ORG_ID", "")
SIMPLISMART_MODEL_REPO_UUID = os.environ.get("SIMPLISMART_MODEL_REPO_UUID", "")

HF_MODEL_ID     = "google/gemma-3-4b-it"
HF_MODEL_CLASS  = "Gemma3ForCausalLM"
ACCELERATOR     = "nvidia-h100"
DEPLOYMENT_NAME = "gemma-3-4b-benchmark"

COMPILE_POLL_INTERVAL_S = 30
COMPILE_TIMEOUT_S       = 3600  # 60 min
DEPLOY_POLL_INTERVAL_S  = 15
DEPLOY_TIMEOUT_S        = 600   # 10 min


def _write_env(key: str, value: str) -> None:
    set_key(str(ENV_PATH), key, value)
    print(f"  -> .env updated: {key}={value}")


def find_existing_compiled_repo(client, list_params_cls) -> str | None:
    """Return UUID of an existing SUCCESS-state model repo with DEPLOYMENT_NAME, or None."""
    try:
        repos = client.list_model_repos(list_params_cls(
            org_id=SIMPLISMART_ORG_ID, offset=0, count=10, name=DEPLOYMENT_NAME,
        ))
        for r in repos.get("results", []):
            if r.get("status") == "SUCCESS":
                uuid = r.get("uuid")
                print(f"[Step 1] Found existing compiled repo '{DEPLOYMENT_NAME}' in SUCCESS state.")
                print(f"         UUID: {uuid} — skipping compilation.")
                return uuid
    except Exception as e:
        print(f"[Step 1] Could not check existing repos: {e}")
    return None


def compile_model(client, compile_create_cls, avatar_cls) -> str:
    """Submit compilation job and return UUID."""
    compile_payload = compile_create_cls(
        name=DEPLOYMENT_NAME,
        description=f"{HF_MODEL_ID} compiled for benchmarking",
        source_type="huggingface",
        source_url=HF_MODEL_ID,
        model_class=HF_MODEL_CLASS,
        accelerator_type=ACCELERATOR,
        use_simplismart_infrastructure=True,
        avatar=avatar_cls(
            image_url="https://huggingface.co/google/gemma-3-4b-it/resolve/main/thumbnail.jpg",
        ),
    )
    data = client.create_model_repo_private_compile(compile_payload)
    uuid = data.get("uuid") or data.get("id")
    print(f"[Step 1] Compile job submitted.")
    print(f"         Name   : {data.get('name')}")
    print(f"         UUID   : {uuid}")
    print(f"         Status : {data.get('status')}")
    _write_env("SIMPLISMART_MODEL_REPO_UUID", uuid)
    return uuid


def poll_compilation(client, list_params_cls, model_repo_uuid: str) -> None:
    """Poll until compilation reaches SUCCESS or raises on failure/timeout."""
    print(f"\n[Step 2] Polling for compilation (timeout: {COMPILE_TIMEOUT_S // 60} min)...")
    list_params = list_params_cls(org_id=SIMPLISMART_ORG_ID, offset=0, count=1, name=DEPLOYMENT_NAME)
    prev_status = None
    start = time.time()
    while time.time() - start < COMPILE_TIMEOUT_S:
        try:
            repos = client.list_model_repos(list_params)
            results = repos.get("results", [])
            if not results:
                time.sleep(COMPILE_POLL_INTERVAL_S)
                continue
            result = results[0]
            status = result.get("status", "UNKNOWN")
            if status != prev_status:
                elapsed = int(time.time() - start)
                print(f"[Step 2] {model_repo_uuid}: {status} ({elapsed}s elapsed)")
                prev_status = status
            if status == "SUCCESS":
                return
            if status in ("FAILED", "ERROR", "CANCELLED"):
                print(f"[Step 2] Compilation failed: {result}")
                sys.exit(1)
        except Exception as e:
            print(f"[Step 2] Poll error: {e}")
        time.sleep(COMPILE_POLL_INTERVAL_S)
    print(f"[Step 2] Timed out after {COMPILE_TIMEOUT_S // 60} minutes.")
    sys.exit(1)


def create_deployment(client, deploy_create_cls, model_repo_uuid: str) -> tuple[str, str]:
    """Create deployment and return (deployment_id, model_endpoint)."""
    deploy_payload = deploy_create_cls(
        org=SIMPLISMART_ORG_ID,
        model_repo=model_repo_uuid,
        gpu_id=ACCELERATOR,
        name=DEPLOYMENT_NAME,
        min_pod_replicas=1,
        max_pod_replicas=1,
        scale_to_zero_enabled=True,
    )
    deployment = client.create_deployment(deploy_payload)
    deployment_id = deployment.get("deployment_id") or deployment.get("id") or deployment.get("uuid")
    model_endpoint = deployment.get("model_endpoint", "")
    print(f"[Step 3] Deployment created.")
    print(f"         ID       : {deployment_id}")
    print(f"         Name     : {deployment.get('name')}")
    if model_endpoint:
        print(f"         Endpoint : https://{model_endpoint}")
    return deployment_id, model_endpoint


def poll_health(client, deployment_id: str, model_endpoint: str) -> None:
    """Poll until deployment is Healthy, then write env vars."""
    print(f"\n[Step 4] Polling for healthy status (timeout: {DEPLOY_TIMEOUT_S // 60} min)...")
    start = time.time()
    while time.time() - start < DEPLOY_TIMEOUT_S:
        try:
            health = client.fetch_deployment_health(deployment_id=deployment_id)
            health_status = health.get("data", "unknown")
            msg = ""
            if health.get("messages"):
                msg = health["messages"][0].get("message", "")
            elapsed = int(time.time() - start)
            print(f"[Step 4] Health: {health_status} ({elapsed}s) {msg}")

            if health_status == "Healthy":
                detail = client.get_model_deployment(deployment_id=deployment_id)
                endpoint = detail.get("model_endpoint") or detail.get("endpoint") or model_endpoint
                if endpoint and not endpoint.startswith("http"):
                    endpoint = f"https://{endpoint}"
                if not endpoint:
                    endpoint = "https://api.simplismart.live"
                print(f"\n[Step 4] Deployment healthy!")
                print(f"         Inference endpoint: {endpoint}")
                _write_env("SIMPLISMART_BASE_URL", endpoint)
                _write_env("SIMPLISMART_DEPLOYMENT_ID", deployment_id)
                print("\n[Simplismart] .env updated. Ready for benchmarking.")
                print("\nREMINDER: python deploy/teardown_simplismart.py  (after benchmarking)")
                return
            if health_status in ("Failed", "Error", "Stopped"):
                print(f"[Step 4] Deployment failed: {health}")
                sys.exit(1)
        except Exception as e:
            print(f"[Step 4] Health poll error: {e}")
        time.sleep(DEPLOY_POLL_INTERVAL_S)

    print(f"[Step 4] Deployment did not become healthy within {DEPLOY_TIMEOUT_S // 60} minutes.")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Gemma 3 4B Instruct on Simplismart")
    parser.add_argument(
        "--deploy-only", action="store_true",
        help="Skip compilation. Requires SIMPLISMART_MODEL_REPO_UUID in .env.",
    )
    args = parser.parse_args()

    if not SIMPLISMART_API_KEY:
        print("[Simplismart] ERROR: SIMPLISMART_API_KEY not set in .env")
        sys.exit(1)
    if not SIMPLISMART_ORG_ID:
        print("[Simplismart] ERROR: SIMPLISMART_ORG_ID not set in .env")
        sys.exit(1)

    from simplismart import Simplismart, ModelRepoCompileCreate, ModelRepoListParams, DeploymentCreate
    from simplismart.models.model_repo import ModelRepoCompileAvatar

    client = Simplismart(pg_token=SIMPLISMART_API_KEY)

    print("\n" + "=" * 60)
    print("SIMPLISMART DEPLOYMENT — Gemma 3 4B Instruct")
    print("=" * 60)
    print(f"Model : {HF_MODEL_ID}")
    print(f"GPU   : {ACCELERATOR}")
    print(f"Org   : {SIMPLISMART_ORG_ID}")

    # ------------------------------------------------------------------ #
    # Step 1: Resolve model repo UUID (compile or reuse existing)
    # ------------------------------------------------------------------ #
    model_repo_uuid = None

    if args.deploy_only:
        # Explicit flag: must have UUID in env
        if not SIMPLISMART_MODEL_REPO_UUID:
            print("[Simplismart] ERROR: --deploy-only requires SIMPLISMART_MODEL_REPO_UUID in .env")
            sys.exit(1)
        model_repo_uuid = SIMPLISMART_MODEL_REPO_UUID
        print(f"\n[Step 1] --deploy-only: using existing model repo {model_repo_uuid}")
    elif SIMPLISMART_MODEL_REPO_UUID:
        # UUID already in env from a previous compile run
        model_repo_uuid = SIMPLISMART_MODEL_REPO_UUID
        print(f"\n[Step 1] SIMPLISMART_MODEL_REPO_UUID found in .env: {model_repo_uuid} — skipping compile.")
    else:
        # Check if a SUCCESS-state repo with this name already exists
        print(f"\n[Step 1] Checking for existing compiled repo named '{DEPLOYMENT_NAME}'...")
        model_repo_uuid = find_existing_compiled_repo(client, ModelRepoListParams)

        if not model_repo_uuid:
            # Fresh compile
            print(f"[Step 1] No existing compiled repo found. Starting compilation of {HF_MODEL_ID}...")
            print(f"         Compile time: ~20-60 min. GPU billing has NOT started yet.")
            try:
                model_repo_uuid = compile_model(client, ModelRepoCompileCreate, ModelRepoCompileAvatar)
            except Exception as exc:
                print(f"[Step 1] Compile submission failed: {type(exc).__name__}: {exc}")
                sys.exit(1)

            # Poll for compile completion
            poll_compilation(client, ModelRepoListParams, model_repo_uuid)
            print(f"[Step 2] Compilation complete. UUID: {model_repo_uuid}")

    # ------------------------------------------------------------------ #
    # Step 3: Cost checkpoint + create deployment
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("COST CHECKPOINT")
    print("=" * 60)
    print(f"Action  : Deploy compiled {HF_MODEL_ID} on Simplismart {ACCELERATOR}")
    print(f"Pricing : ~$1.99/hr per H100 GPU (dedicated, billed while active)")
    print(f"Scale   : scale_to_zero_enabled=True — billing stops when idle")
    print(f"Budget  : Hard limit $5 on Simplismart")
    print(f"Repo    : {model_repo_uuid}")
    print("")
    print("AWAITING APPROVAL — type 'yes' to proceed or anything else to abort:")
    answer = input("> ").strip().lower()
    if answer != "yes":
        print("Aborted. Compiled model repo is preserved — re-run with --deploy-only to retry.")
        sys.exit(0)

    print(f"\n[Step 3] Creating dedicated deployment on {ACCELERATOR}...")
    print(f"         scale_to_zero_enabled=True — GPU stops billing when idle")

    try:
        deployment_id, model_endpoint = create_deployment(client, DeploymentCreate, model_repo_uuid)
    except Exception as exc:
        print(f"[Step 3] Deployment creation failed: {type(exc).__name__}: {exc}")
        # Print all available details from the exception
        for attr in ("response", "body", "detail", "message", "args"):
            val = getattr(exc, attr, None)
            if val:
                print(f"         {attr}: {val}")
        if hasattr(exc, "__dict__"):
            print(f"         exc.__dict__: {exc.__dict__}")
        print(f"         Compiled repo {model_repo_uuid} is preserved.")
        print(f"         Re-run with --deploy-only to retry without recompiling.")
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Step 4: Poll for healthy status
    # ------------------------------------------------------------------ #
    poll_health(client, deployment_id, model_endpoint)


if __name__ == "__main__":
    main()
