"""RunPod Hub public-endpoint tools (Melody's RunPod account).

image_generation: z-image-turbo (text->image), nano-banana-pro-edit (edit / reference images)
video_generation: seedance-v1-5-pro-i2v (image->video)
avatar:          infinitetalk (photo + audio -> talking video)
tts:             chatterbox-turbo
analysis:        whisper-v3-large (transcription)
"""
from __future__ import annotations
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (BaseTool, Determinism, ExecutionMode, ResourceProfile, RetryPolicy,
                             ToolResult, ToolRuntime, ToolStability, ToolStatus, ToolTier)
from tools.runpod import _client as rp

_INSTALL = "Set RUNPOD_API_KEY (RunPod console -> Settings -> API Keys) in OpenMontage/.env"


class _RunPodBase(BaseTool):
    version = "0.1.0"
    provider = "runpod"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API
    dependencies = []
    install_instructions = _INSTALL
    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=200, network_required=True)
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=["timeout"])
    side_effects = ["calls RunPod Hub public endpoint (bills the RunPod account)", "writes output file"]

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE if rp.key() else ToolStatus.UNAVAILABLE

    def _go(self, endpoint: str, payload: dict, out: str, ext: str, model: str, cost: float, extra: dict | None = None):
        if not rp.key():
            return ToolResult(success=False, error="RUNPOD_API_KEY not set. " + _INSTALL)
        t0 = time.time()
        try:
            st = rp.run(endpoint, payload)
            url = rp.result_url(st)
            out = out or f"runpod_{endpoint}_{int(t0)}{ext}"
            rp.download(url, out)
        except Exception as e:
            return ToolResult(success=False, error=f"RunPod {endpoint} failed: {e}")
        c = (st.get("output") or {}).get("cost", cost) if isinstance(st.get("output"), dict) else cost
        data = {"provider": "runpod", "model": model, "output": out, "source_url": url, "job_id": st.get("id")}
        data.update(extra or {})
        return ToolResult(success=True, data=data, artifacts=[out], cost_usd=c,
                          duration_seconds=round(time.time() - t0, 2), model=model)


class RunPodImage(_RunPodBase):
    name = "runpod_image"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    agent_skills = ["flux-best-practices"]
    capabilities = ["generate_image", "text_to_image", "edit_image", "image_to_image"]
    supports = {"image_edit": True, "aspect_ratio": True, "reference_image": True, "multiple_reference_images": True}
    best_for = ["fast cheap stills (z-image-turbo ~$0.005)", "identity-preserving edits of a real photo (nano-banana-pro-edit $0.14)"]
    not_good_for = ["readable text inside images"]
    input_schema = {"type": "object", "required": ["prompt"], "properties": {
        "prompt": {"type": "string"},
        "model": {"type": "string", "enum": ["z-image-turbo", "nano-banana-pro-edit"], "default": "z-image-turbo"},
        "size": {"type": "string", "default": "720*1280", "description": "z-image-turbo only, e.g. 720*1280"},
        "aspect_ratio": {"type": "string", "description": "nano-banana only, e.g. 9:16, 3:4"},
        "resolution": {"type": "string", "enum": ["1k", "2k", "4k"], "default": "2k"},
        "reference_images": {"type": "array", "items": {"type": "string"}, "description": "local paths or URLs (nano-banana)"},
        "output_path": {"type": "string"}}}
    idempotency_key_fields = ["prompt", "model", "size", "aspect_ratio"]

    def estimate_cost(self, inputs):
        return 0.14 if inputs.get("model") == "nano-banana-pro-edit" else 0.005

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        m = inputs.get("model") or ("nano-banana-pro-edit" if inputs.get("reference_images") else "z-image-turbo")
        if m == "nano-banana-pro-edit":
            p = {"prompt": inputs["prompt"], "resolution": inputs.get("resolution", "2k"), "output_format": "jpeg",
                 "images": [rp.upload(x) for x in inputs.get("reference_images") or []]}
            if inputs.get("aspect_ratio"):
                p["aspect_ratio"] = inputs["aspect_ratio"]
            return self._go(m, p, inputs.get("output_path"), ".jpg", m, 0.14)
        p = {"prompt": inputs["prompt"], "size": inputs.get("size", "720*1280"), "seed": -1, "output_format": "png", "enable_safety_checker": True}
        return self._go(m, p, inputs.get("output_path"), ".png", m, 0.005)


class RunPodSeedance(_RunPodBase):
    name = "runpod_seedance"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    agent_skills = ["seedance-2-0", "ai-video-gen"]
    capabilities = ["image_to_video"]
    supports = {"image_to_video": True, "aspect_ratio": True, "duration": True}
    best_for = ["5-10s motion clips from an approved still (walking, turning, camera push-in)"]
    not_good_for = ["readable text", "long continuous shots"]
    input_schema = {"type": "object", "required": ["prompt", "image"], "properties": {
        "prompt": {"type": "string"}, "image": {"type": "string", "description": "local path or URL of first frame"},
        "duration": {"type": "integer", "default": 5}, "resolution": {"type": "string", "enum": ["480p", "720p", "1080p"], "default": "720p"},
        "aspect_ratio": {"type": "string", "default": "9:16"}, "camera_fixed": {"type": "boolean", "default": False},
        "output_path": {"type": "string"}}}
    idempotency_key_fields = ["prompt", "image", "duration", "resolution"]

    def estimate_cost(self, inputs):
        return 0.12 * max(1, int(inputs.get("duration", 5)) / 5)

    def execute(self, inputs):
        p = {"prompt": inputs["prompt"], "image": rp.upload(inputs["image"]), "duration": int(inputs.get("duration", 5)),
             "resolution": inputs.get("resolution", "720p"), "aspect_ratio": inputs.get("aspect_ratio", "9:16"),
             "camera_fixed": bool(inputs.get("camera_fixed", False)), "generate_audio": False, "seed": -1}
        return self._go("seedance-v1-5-pro-i2v", p, inputs.get("output_path"), ".mp4", "seedance-v1-5-pro-i2v", self.estimate_cost(inputs))


class RunPodInfiniteTalk(_RunPodBase):
    name = "runpod_infinitetalk"
    tier = ToolTier.GENERATE
    capability = "avatar"
    agent_skills = ["avatar-video"]
    capabilities = ["talking_head", "lip_sync", "photo_to_avatar"]
    supports = {"lip_sync": True, "custom_avatar_photo": True}
    best_for = ["a real person's photo speaking supplied audio (480p ~$0.25/clip, ~1.5-3 min)"]
    not_good_for = ["full-body motion"]
    input_schema = {"type": "object", "required": ["image", "audio"], "properties": {
        "image": {"type": "string"}, "audio": {"type": "string"},
        "prompt": {"type": "string", "default": "A woman talks naturally and warmly to the camera, expressive face, natural blinks, subtle head and shoulder movement, realistic."},
        "resolution": {"type": "string", "enum": ["480p", "720p"], "default": "480p"}, "output_path": {"type": "string"}}}
    idempotency_key_fields = ["image", "audio", "prompt", "resolution"]

    def estimate_cost(self, inputs):
        return 0.25 if inputs.get("resolution", "480p") == "480p" else 0.5

    def execute(self, inputs):
        p = {"prompt": inputs.get("prompt") or self.input_schema["properties"]["prompt"]["default"],
             "image": rp.upload(inputs["image"]), "audio": rp.upload(inputs["audio"]),
             "resolution": inputs.get("resolution", "480p"), "enable_safety_checker": True}
        return self._go("infinitetalk", p, inputs.get("output_path"), ".mp4", "infinitetalk", self.estimate_cost(inputs))


class RunPodChatterboxTTS(_RunPodBase):
    name = "runpod_chatterbox_tts"
    tier = ToolTier.VOICE if hasattr(ToolTier, "VOICE") else ToolTier.GENERATE
    capability = "tts"
    agent_skills = ["text-to-speech"]
    capabilities = ["text_to_speech"]
    supports = {"voice_selection": True}
    best_for = ["cheap natural narration on RunPod"]
    not_good_for = ["cloning a specific person's voice"]
    input_schema = {"type": "object", "required": ["text"], "properties": {
        "text": {"type": "string"}, "voice": {"type": "string", "default": "lucy"},
        "format": {"type": "string", "default": "wav"}, "output_path": {"type": "string"}}}
    idempotency_key_fields = ["text", "voice"]

    def estimate_cost(self, inputs):
        return 0.01

    def execute(self, inputs):
        p = {"prompt": inputs["text"], "voice": inputs.get("voice", "lucy"), "format": inputs.get("format", "wav")}
        return self._go("chatterbox-turbo", p, inputs.get("output_path"), "." + inputs.get("format", "wav"), "chatterbox-turbo", 0.01)


class RunPodWhisper(_RunPodBase):
    name = "runpod_whisper"
    tier = ToolTier.ANALYZE if hasattr(ToolTier, "ANALYZE") else ToolTier.GENERATE
    capability = "analysis"
    agent_skills = ["speech-to-text"]
    capabilities = ["transcribe"]
    supports = {"transcription": True}
    best_for = ["transcribing voice memos / long recordings (chunked)"]
    not_good_for = ["word-level timestamps"]
    input_schema = {"type": "object", "required": ["audio"], "properties": {
        "audio": {"type": "string"}, "language": {"type": "string", "default": "en"}, "output_path": {"type": "string"}}}
    idempotency_key_fields = ["audio"]

    def estimate_cost(self, inputs):
        return 0.006

    def execute(self, inputs):
        import base64
        t0 = time.time()
        try:
            b = base64.b64encode(Path(inputs["audio"]).read_bytes()).decode()
            st = rp.run("whisper-v3-large", {"audio_base64": b, "language": inputs.get("language", "en")})
            text = st["output"]["result"]
        except Exception as e:
            return ToolResult(success=False, error=f"RunPod whisper failed: {e}")
        out = inputs.get("output_path")
        if out:
            Path(out).parent.mkdir(parents=True, exist_ok=True); Path(out).write_text(text)
        return ToolResult(success=True, data={"provider": "runpod", "text": text, "output": out}, artifacts=[out] if out else [],
                          cost_usd=st["output"].get("cost", 0.006), duration_seconds=round(time.time() - t0, 2), model="whisper-v3-large")
