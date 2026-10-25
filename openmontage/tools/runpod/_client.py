"""Shared RunPod Hub public-endpoint client (upload, run, poll, download)."""
from __future__ import annotations
import base64, mimetypes, os, time
from pathlib import Path
import requests

API = "https://api.runpod.ai/v2"
UPLOADER = "kyy4e07yda8eth"  # RunPod Hub media uploader used by the console playgrounds
UA = {"User-Agent": "Mozilla/5.0"}

def key() -> str | None:
    return os.environ.get("RUNPOD_API_KEY")

def _h():
    return {"Authorization": f"Bearer {key()}", "Content-Type": "application/json"}

def upload(path_or_url: str) -> str:
    """Return a public URL for a local file (uploads via the Hub uploader); URLs pass through."""
    if str(path_or_url).startswith(("http://", "https://")):
        return str(path_or_url)
    p = Path(path_or_url)
    ct = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    body = {"input": {"image": base64.b64encode(p.read_bytes()).decode(), "content_type": ct}}
    r = requests.post(f"{API}/{UPLOADER}/runsync", json=body, headers=_h(), timeout=300)
    r.raise_for_status()
    out = r.json().get("output") or {}
    url = out.get("result") if isinstance(out, dict) else None
    if not url:
        raise RuntimeError(f"RunPod upload failed: {r.text[:300]}")
    return url

def run(endpoint: str, payload: dict, timeout_s: int = 1800, poll_s: float = 5.0) -> dict:
    r = requests.post(f"{API}/{endpoint}/run", json={"input": payload}, headers=_h(), timeout=120)
    r.raise_for_status()
    jid = r.json()["id"]
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        s = requests.get(f"{API}/{endpoint}/status/{jid}", headers=_h(), timeout=60).json()
        st = s.get("status")
        if st == "COMPLETED":
            return s
        if st in ("FAILED", "CANCELLED", "TIMED_OUT"):
            raise RuntimeError(f"RunPod {endpoint} job {st}: {str(s)[:400]}")
        time.sleep(poll_s)
    requests.post(f"{API}/{endpoint}/cancel/{jid}", headers=_h(), timeout=30)
    raise TimeoutError(f"RunPod {endpoint} job {jid} timed out")

def result_url(status: dict) -> str:
    out = status.get("output")
    if isinstance(out, dict):
        res = out.get("result") or out.get("output") or out.get("url")
        if isinstance(res, list):
            res = res[0]
        if res:
            return res
    if isinstance(out, str):
        return out
    raise RuntimeError(f"No result URL in RunPod output: {str(status)[:300]}")

def download(url: str, dest: str) -> str:
    d = Path(dest); d.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, headers=UA, timeout=600); r.raise_for_status()
    d.write_bytes(r.content)
    return str(d)
