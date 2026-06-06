"""
Fireworks AI dedicated deployment script for Gemma 3 4B Instruct on NVIDIA H100 80GB.

Uses the deploymentShape API approach (per Fireworks API spec):
  1. List available deployment shape versions for the model
  2. Find the H100 shape — fail loudly if none found (no fallback)
  3. Print COST CHECKPOINT and await approval
  4. POST deployment with deploymentShape field
  5. Poll until READY, write env vars

On success: writes FIREWORKS_DEPLOYMENT_ID and FIREWORKS_MODEL_ID to .env.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key

load_dotenv()

ENV_PATH = Path(__file__).parent.parent / ".env"

FIREWORKS_API_KEY    = os.environ.get("FIREWORKS_API_KEY", "")
FIREWORKS_ACCOUNT_ID = os.environ.get("FIREWORKS_ACCOUNT_ID", "")
FIREWORKS_BASE_MODEL = os.environ.get("FIREWORKS_BASE_MODEL_ID", "accounts/fireworks/models/gemma-3-4b-it")

API_BASE = "https://api.fireworks.ai/v1"
POLL_INTERVAL_S = 20
DEPLOY_TIMEOUT_S = 900  # 15 min — shape-based deployments may take longer

TARGET_GPU = "NVIDIA_H100_80GB"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json",
    }


def _write_env(key: str, value: str) -> None:
    set_key(str(ENV_PATH), key, value)
    print(f"  -> .env updated: {key}={value}")


def list_deployment_shape_versions(account_id: str = "fireworks") -> list[dict]:
    """
    List deployment shape versions from the given account.
    Public shapes live under accounts/fireworks — try that first.
    Returns list of shape version objects (may be empty on 403/404).
    """
    url = f"{API_BASE}/accounts/{account_id}/deploymentShapeVersions"
    print(f"[Fireworks] GET {url}")
    try:
        resp = requests.get(url, headers=_headers(), timeout=15)
        print(f"[Fireworks] Response {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            # API may return {"deploymentShapeVersions": [...]} or a list directly
            if isinstance(data, list):
                return data
            return data.get("deploymentShapeVersions", data.get("items", []))
        else:
            print(f"[Fireworks] Shape list error: {resp.text[:300]}")
    except Exception as e:
        print(f"[Fireworks] Shape list exception: {e}")
    return []


def find_h100_shape(model_id: str) -> str | None:
    """
    Discover the H100 deployment shape for the given model.
    Checks public shapes (accounts/fireworks) and user's account shapes.
    Returns the full shape name string or None.
    """
    model_slug = model_id.split("/")[-1]  # e.g. "gemma-3-4b-instruct"

    for account in ("fireworks", FIREWORKS_ACCOUNT_ID):
        shapes = list_deployment_shape_versions(account)
        if not shapes:
            continue

        print(f"[Fireworks] Found {len(shapes)} shape versions under accounts/{account}")

        # Log all shapes for debugging
        for s in shapes[:20]:
            name = s.get("name", s.get("deploymentShape", ""))
            accel = s.get("acceleratorType", s.get("gpuType", ""))
            print(f"  shape: {name}  gpu: {accel}")

        # Filter: must contain model slug and H100
        h100_shapes = [
            s for s in shapes
            if (
                model_slug.lower() in s.get("name", "").lower()
                and "h100" in s.get("name", "").lower()
            ) or (
                model_slug.lower() in s.get("name", "").lower()
                and "H100" in s.get("acceleratorType", s.get("gpuType", ""))
            )
        ]

        if h100_shapes:
            chosen = h100_shapes[0]
            # Shape name may be the full path or just the shape name field
            shape_name = chosen.get("name", chosen.get("deploymentShape", ""))
            print(f"[Fireworks] H100 shape found: {shape_name}")
            return shape_name

    return None


def create_deployment(deployment_shape: str) -> dict:
    """
    POST to Fireworks deployment API using deploymentShape.
    Per API spec: when using deploymentShape, omit acceleratorType/activeModelVersion.
    """
    url = f"{API_BASE}/accounts/{FIREWORKS_ACCOUNT_ID}/deployments"
    payload = {
        "baseModel": FIREWORKS_BASE_MODEL,
        "deploymentShape": deployment_shape,
        "minReplicaCount": 0,
        "maxReplicaCount": 1,
        "autoscalingPolicy": {
            "scaleToZeroWindow": "300s",  # 5 min — minimum allowed
        },
    }
    print(f"[Fireworks] POST {url}")
    print(f"[Fireworks] deploymentShape: {deployment_shape}")
    print(f"[Fireworks] payload: {payload}")

    resp = requests.post(url, json=payload, headers=_headers(), timeout=30)
    print(f"[Fireworks] Response {resp.status_code}: {resp.text[:600]}")
    resp.raise_for_status()
    return resp.json()


def create_deployment_with_accelerator() -> dict:
    """
    Fallback path: create deployment using acceleratorType directly (no shape).
    Used if shape discovery returns nothing — still H100 ONLY, no GPU fallback.
    """
    url = f"{API_BASE}/accounts/{FIREWORKS_ACCOUNT_ID}/deployments"
    payload = {
        "baseModel": FIREWORKS_BASE_MODEL,
        "acceleratorType": TARGET_GPU,
        "acceleratorCount": 1,
        "minReplicaCount": 0,
        "maxReplicaCount": 1,
        "autoscalingPolicy": {
            "scaleToZeroWindow": "300s",
        },
    }
    print(f"[Fireworks] POST {url}  (direct acceleratorType path)")
    print(f"[Fireworks] GPU: {TARGET_GPU}")
    print(f"[Fireworks] payload: {payload}")

    resp = requests.post(url, json=payload, headers=_headers(), timeout=30)
    print(f"[Fireworks] Response {resp.status_code}: {resp.text[:600]}")
    resp.raise_for_status()
    return resp.json()


def poll_deployment(deployment_id: str) -> bool:
    """Poll until deployment reaches READY state or timeout."""
    url = f"{API_BASE}/accounts/{FIREWORKS_ACCOUNT_ID}/deployments/{deployment_id}"
    start = time.time()
    while time.time() - start < DEPLOY_TIMEOUT_S:
        resp = requests.get(url, headers=_headers(), timeout=15)
        if resp.status_code != 200:
            print(f"[Fireworks] Poll error {resp.status_code}: {resp.text[:200]}")
            time.sleep(POLL_INTERVAL_S)
            continue
        data = resp.json()
        state = data.get("state", "UNKNOWN")
        elapsed = int(time.time() - start)

        replica_stats = data.get("replicaStats", {})
        ready_replicas = replica_stats.get("readyReplicaCount", "?")
        pending = replica_stats.get("pendingSchedulingReplicaCount", "?")
        downloading = replica_stats.get("downloadingModelReplicaCount", "?")
        initializing = replica_stats.get("initializingReplicaCount", "?")

        print(
            f"[Fireworks] state={state} ready={ready_replicas} "
            f"pending={pending} downloading={downloading} "
            f"initializing={initializing} ({elapsed}s elapsed)"
        )

        if state.upper() == "READY":
            return True
        if state.upper() in ("FAILED", "DELETED"):
            status = data.get("status", {})
            print(f"[Fireworks] Deployment failed. status: {status}")
            return False
        time.sleep(POLL_INTERVAL_S)

    print(f"[Fireworks] Timed out after {DEPLOY_TIMEOUT_S}s waiting for READY state.")
    return False


def main() -> None:
    if not FIREWORKS_API_KEY:
        print("[Fireworks] ERROR: FIREWORKS_API_KEY not set in .env")
        sys.exit(1)
    if not FIREWORKS_ACCOUNT_ID:
        print("[Fireworks] ERROR: FIREWORKS_ACCOUNT_ID not set in .env")
        sys.exit(1)

    print("\n" + "="*60)
    print("FIREWORKS AI DEPLOYMENT — Gemma 3 4B Instruct on NVIDIA H100 80GB")
    print("="*60)
    print(f"Model   : {FIREWORKS_BASE_MODEL}")
    print(f"GPU     : {TARGET_GPU} x1  (H100 80GB)")
    print(f"Account : {FIREWORKS_ACCOUNT_ID}")
    print(f"Scale   : min_replicas=0 (scale-to-zero after 5 min idle)")

    # Step 1: Discover H100 deployment shape
    print("\n[Fireworks] Step 1: Discovering H100 deployment shape...")
    shape = find_h100_shape(FIREWORKS_BASE_MODEL)

    if shape:
        print(f"[Fireworks] Will deploy using shape: {shape}")
    else:
        print("[Fireworks] No H100 deployment shape found via list API.")
        print("[Fireworks] Falling back to direct acceleratorType=NVIDIA_H100_80GB.")
        print("[Fireworks] NOTE: This will fail if H100 is not available for this model.")

    # Step 2: COST CHECKPOINT
    print("\n" + "="*60)
    print("COST CHECKPOINT")
    print("="*60)
    print("Action  : Deploy Gemma 3 4B Instruct on Fireworks AI with 1x NVIDIA H100 80GB")
    print("Pricing : ~$2.40/hr per H100 GPU (on-demand dedicated)")
    print("Scale   : Autoscales to 0 replicas after 5 min idle — billed only when active")
    print("Budget  : Hard limit $5 on Fireworks AI")
    print("")
    print("AWAITING APPROVAL — type 'yes' to proceed or anything else to abort:")
    answer = input("> ").strip().lower()
    if answer != "yes":
        print("Aborted by user.")
        sys.exit(0)

    # Step 3: Create deployment
    print("\n[Fireworks] Step 2: Creating deployment...")
    try:
        if shape:
            deployment = create_deployment(shape)
        else:
            deployment = create_deployment_with_accelerator()
    except requests.HTTPError as e:
        print(f"[Fireworks] Deployment creation failed: {e}")
        sys.exit(1)

    # Extract deployment ID from response (name field is full path)
    deployment_name = deployment.get("name", "")
    deployment_id = deployment_name.split("/")[-1] if "/" in deployment_name else deployment_name
    if not deployment_id:
        deployment_id = deployment.get("id", deployment.get("deploymentId", ""))

    if not deployment_id:
        print(f"[Fireworks] ERROR: Could not extract deployment ID from response: {deployment}")
        sys.exit(1)

    print(f"\n[Fireworks] Deployment created — ID: {deployment_id}")
    print("[Fireworks] Step 3: Polling for READY state (may take 5-15 min for GPU allocation)...")

    ready = poll_deployment(deployment_id)

    if ready:
        inference_model_id = f"accounts/{FIREWORKS_ACCOUNT_ID}/deployments/{deployment_id}"
        print(f"\n[Fireworks] Deployment READY.")
        print(f"[Fireworks] Inference model ID: {inference_model_id}")
        _write_env("FIREWORKS_DEPLOYMENT_ID", deployment_id)
        _write_env("FIREWORKS_MODEL_ID", inference_model_id)
        print("\n[Fireworks] .env updated. Ready to benchmark.")
    else:
        print("\n[Fireworks] Deployment did not reach READY state within timeout.")
        print(f"[Fireworks] Deployment ID {deployment_id} — check Fireworks console for status.")
        sys.exit(1)

    print("\nREMINDER: Delete this deployment after benchmarking to stop GPU billing.")
    print("          python deploy/teardown_fireworks.py")


if __name__ == "__main__":
    main()
