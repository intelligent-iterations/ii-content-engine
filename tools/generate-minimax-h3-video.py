#!/usr/bin/env python3
"""Render a pinned MiniMax H3 T2VA workflow through a local ComfyUI server."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from typing import Any
import urllib.error
import urllib.request


COMFY_COMMIT = "531ea7db139a856a830182694441e9755f0e260a"
MODEL_REPO = "Comfy-Org/MiniMax-H3"
MODEL_REVISION = "eb8a16107c595128b3a578f82d2ce2f75920c355"
MODEL_LICENSE = "minimax-h3-community-license-agreement"
MODEL_FILES = {
    "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors": {
        "size": 20_970_379_616,
        "sha256": "e889202c41dafb67b10d67b97f0d8541508036a6090af23425a5c2615d03c47a",
    },
    "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors": {
        "size": 15_687_142_551,
        "sha256": "35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6",
    },
    "vae/minimax_h3_video_vae_fp16.safetensors": {
        "size": 5_207_808_496,
        "sha256": "7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522",
    },
    "vae/minimax_h3_audio_vae_fp32.safetensors": {
        "size": 605_254_808,
        "sha256": "8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def aligned_frame_count(seconds: float, fps: int = 24) -> int:
    frames = max(5, round(seconds * fps))
    return frames + (5 - frames % 17) % 17


def validate_profile(args: argparse.Namespace) -> int:
    if args.width % 32 or args.height % 32:
        raise ValueError("source width and height must be divisible by 32")
    if args.width * args.height > 768 * 1344:
        raise ValueError("source canvas exceeds MiniMax H3's 768x1344 native area")
    if args.fps != 24:
        raise ValueError("MiniMax H3 native generation requires 24 fps")
    if not 0 < args.duration <= 15:
        raise ValueError("duration must be greater than zero and at most 15 seconds")
    if args.steps != 20:
        raise ValueError("the pinned official quality profile requires exactly 20 steps")
    if args.final_width != 1280 or args.final_height != 720 or args.final_duration != 15:
        raise ValueError("this acceptance profile requires exactly 1280x720 for 15.000 seconds")
    return aligned_frame_count(args.duration, args.fps)


def ensure_comfy_revision(comfy_dir: Path) -> None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=comfy_dir, check=True, text=True, capture_output=True
    )
    got = result.stdout.strip()
    if got != COMFY_COMMIT:
        raise RuntimeError(f"ComfyUI revision mismatch: got {got}, expected {COMFY_COMMIT}")


def ensure_models(cache_dir: Path) -> tuple[Path, list[dict[str, Any]]]:
    model_dir = cache_dir / "huggingface" / MODEL_REPO
    missing_bytes = 0
    for relative, spec in MODEL_FILES.items():
        path = model_dir / relative
        if path.exists() and (not path.is_file() or path.stat().st_size != spec["size"]):
            raise RuntimeError(
                f"refusing to overwrite unexpected durable model-cache entry: {path}"
            )
        if not path.exists():
            missing_bytes += spec["size"]
    model_dir.mkdir(parents=True, exist_ok=True)
    if missing_bytes:
        free = shutil.disk_usage(cache_dir).free
        if free < missing_bytes + 8 * 1024**3:
            raise RuntimeError(
                f"model cache needs {missing_bytes + 8 * 1024**3} free bytes but has {free}; "
                "refusing to remove existing cache data"
            )
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=MODEL_REPO,
            revision=MODEL_REVISION,
            allow_patterns=sorted(MODEL_FILES),
            local_dir=model_dir,
            max_workers=2,
        )

    verified: list[dict[str, Any]] = []
    for relative, spec in MODEL_FILES.items():
        path = model_dir / relative
        if not path.is_file():
            raise RuntimeError(f"missing model file after download: {path}")
        size = path.stat().st_size
        if size != spec["size"]:
            raise RuntimeError(f"model size mismatch for {path}: got {size}, expected {spec['size']}")
        digest = sha256_file(path)
        if digest != spec["sha256"]:
            raise RuntimeError(f"model sha256 mismatch for {path}: got {digest}, expected {spec['sha256']}")
        verified.append({"path": str(path), "size": size, "sha256": digest})
    return model_dir, verified


def install_models(model_dir: Path, comfy_dir: Path) -> None:
    for relative in MODEL_FILES:
        source = model_dir / relative
        destination = comfy_dir / "models" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.unlink(missing_ok=True)
        destination.symlink_to(source)


def build_prompt_graph(prompt: str, args: argparse.Namespace, frames: int) -> dict[str, Any]:
    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
                "weight_dtype": "default",
            },
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
                "type": "minimax",
                "device": "default",
            },
        },
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
        "5": {
            "class_type": "MiniMaxH3ImageToVideo",
            "inputs": {
                "clip": ["2", 0],
                "vae": ["3", 0],
                "prompt": prompt,
                "width": args.width,
                "height": args.height,
                "length": frames,
            },
        },
        "6": {"class_type": "RandomNoise", "inputs": {"noise_seed": args.seed}},
        "7": {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": ["5", 0]}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "9": {
            "class_type": "BasicScheduler",
            "inputs": {"model": ["1", 0], "scheduler": "simple", "steps": args.steps, "denoise": 1.0},
        },
        "10": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["6", 0],
                "guider": ["7", 0],
                "sampler": ["8", 0],
                "sigmas": ["9", 0],
                "latent_image": ["5", 1],
            },
        },
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["10", 0], "vae": ["4", 0]}},
        "13": {
            "class_type": "CreateVideo",
            "inputs": {"images": ["11", 0], "audio": ["12", 0], "fps": 24.0, "bit_depth": 8},
        },
        "14": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["13", 0],
                "filename_prefix": "minimax_h3/raw",
                "format": "mp4",
                "codec": {"codec": "h264", "encoding": {"encoding": "re-encode", "crf": 16}},
            },
        },
    }


def request_json(method: str, url: str, body: Any | None = None, timeout: int = 30) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/json")
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url}: HTTP {error.code}: {detail[:8000]}") from error


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(base_url: str, process: subprocess.Popen[str], timeout: int) -> None:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"ComfyUI exited during startup with status {process.returncode}")
        try:
            request_json("GET", base_url + "/system_stats")
            return
        except Exception as error:  # server startup is deliberately polled
            last = str(error)
            time.sleep(2)
    raise RuntimeError(f"ComfyUI did not become ready: {last}")


def submit_and_wait(base_url: str, graph: dict[str, Any], process: subprocess.Popen[str], timeout: int) -> dict[str, Any]:
    response = request_json("POST", base_url + "/prompt", {"prompt": graph})
    prompt_id = str(response.get("prompt_id") or "")
    if not prompt_id:
        raise RuntimeError(f"ComfyUI did not return a prompt_id: {response}")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"ComfyUI exited during generation with status {process.returncode}")
        history = request_json("GET", base_url + f"/history/{prompt_id}", timeout=60)
        record = history.get(prompt_id) if isinstance(history, dict) else None
        if isinstance(record, dict):
            status = record.get("status") or {}
            if status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI generation failed: {json.dumps(status)[:8000]}")
            if record.get("outputs"):
                return record
        time.sleep(5)
    raise RuntimeError(f"ComfyUI generation timed out after {timeout} seconds")


def find_saved_video(record: dict[str, Any], comfy_dir: Path) -> Path:
    for output in (record.get("outputs") or {}).values():
        if not isinstance(output, dict):
            continue
        for key in ("videos", "gifs", "images"):
            for item in output.get(key) or []:
                if not isinstance(item, dict) or not item.get("filename"):
                    continue
                if str(item.get("type") or "output") != "output":
                    continue
                candidate = comfy_dir / "output" / str(item.get("subfolder") or "") / str(item["filename"])
                if candidate.suffix.lower() in {".mp4", ".mkv", ".webm"} and candidate.is_file():
                    return candidate
    candidates = sorted((comfy_dir / "output" / "minimax_h3").glob("raw*.mp4"), key=lambda p: p.stat().st_mtime)
    if candidates:
        return candidates[-1]
    raise RuntimeError("ComfyUI completed but no saved video was found")


def ffprobe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def finish_video(raw: Path, final: Path, args: argparse.Namespace) -> dict[str, Any]:
    final.parent.mkdir(parents=True, exist_ok=True)
    video_filter = (
        f"scale={args.final_width}:-2:flags=lanczos,"
        f"crop={args.final_width}:{args.final_height},fps={args.fps},"
        f"trim=duration={args.final_duration},setpts=PTS-STARTPTS"
    )
    audio_filter = f"apad=pad_dur={args.final_duration},atrim=duration={args.final_duration},asetpts=PTS-STARTPTS"
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y", "-i", str(raw),
            "-filter_complex", f"[0:v]{video_filter}[v];[0:a]{audio_filter}[a]",
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "15",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "256k",
            "-ar", "48000", "-ac", "2", "-t", f"{args.final_duration:.3f}", str(final),
        ],
        check=True,
    )
    probe = ffprobe(final)
    streams = probe.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    duration = float((probe.get("format") or {}).get("duration") or 0)
    if not video or (video.get("width"), video.get("height")) != (args.final_width, args.final_height):
        raise RuntimeError(f"final video failed resolution gate: {video}")
    if not audio or int(audio.get("channels") or 0) != 2:
        raise RuntimeError(f"final video failed stereo-audio gate: {audio}")
    if abs(duration - args.final_duration) > 0.02:
        raise RuntimeError(f"final video failed duration gate: got {duration}, expected {args.final_duration}")
    if str(video.get("avg_frame_rate")) != "24/1":
        raise RuntimeError(f"final video failed frame-rate gate: {video.get('avg_frame_rate')}")
    return probe


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--comfy-dir", default="/opt/ComfyUI")
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=736)
    parser.add_argument("--duration", type=float, default=15.0)
    parser.add_argument("--final-width", type=int, default=1280)
    parser.add_argument("--final-height", type=int, default=720)
    parser.add_argument("--final-duration", type=float, default=15.0)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260807)
    parser.add_argument("--server-timeout", type=int, default=600)
    parser.add_argument("--generation-timeout", type=int, default=18000)
    parser.add_argument("--comfy-log", default="")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    frames = validate_profile(args)
    prompt_path = Path(args.prompt_file).resolve()
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt or "integrated_multimodal_description:" not in prompt:
        raise ValueError("prompt file must contain a non-empty H3 integrated_multimodal_description")
    cache_dir = Path(args.cache_dir).resolve()
    comfy_dir = Path(args.comfy_dir).resolve()
    output = Path(args.output).resolve()
    metadata_path = Path(args.metadata).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    ensure_comfy_revision(comfy_dir)
    started = time.monotonic()
    model_dir, verified_models = ensure_models(cache_dir)
    install_models(model_dir, comfy_dir)
    graph = build_prompt_graph(prompt, args, frames)
    graph_path = metadata_path.with_name("minimax-h3-workflow-api.json")
    write_json(graph_path, graph)

    log_path = Path(args.comfy_log).resolve() if args.comfy_log else metadata_path.with_name("comfyui-minimax-h3.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    port = free_port()
    command = [
        sys.executable, "main.py", "--listen", "127.0.0.1", "--port", str(port), "--disable-auto-launch",
        "--disable-all-custom-nodes", "--lowvram", "--reserve-vram", "1.0", "--preview-method", "none",
    ]
    env = os.environ.copy()
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True,max_split_size_mb:128")
    env.setdefault("CUDA_MODULE_LOADING", "LAZY")
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=comfy_dir, env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            base_url = f"http://127.0.0.1:{port}"
            wait_for_server(base_url, process, args.server_timeout)
            record = submit_and_wait(base_url, graph, process, args.generation_timeout)
            raw_source = find_saved_video(record, comfy_dir)
        finally:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=30)

    raw = output.with_name(output.stem + "-raw" + raw_source.suffix.lower())
    raw.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_source, raw)
    raw_probe = ffprobe(raw)
    final_probe = finish_video(raw, output, args)
    metadata = {
        "schema_version": 1,
        "accepted": True,
        "mode": "minimax-h3-t2va-comfyui",
        "output": str(output),
        "raw_output": str(raw),
        "sha256": sha256_file(output),
        "raw_sha256": sha256_file(raw),
        "prompt": prompt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_file": str(prompt_path),
        "workflow_api": str(graph_path),
        "model": {"repo": MODEL_REPO, "revision": MODEL_REVISION, "license": MODEL_LICENSE},
        "models": verified_models,
        "comfyui_commit": COMFY_COMMIT,
        "source": {"width": args.width, "height": args.height, "frames": frames, "fps": args.fps},
        "final": {"width": args.final_width, "height": args.final_height, "duration": args.final_duration},
        "steps": args.steps,
        "seed": args.seed,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "raw_probe": raw_probe,
        "output_probe": final_probe,
        "native_audio": True,
        "generated_speech_requested": False,
        "comfy_log": str(log_path),
    }
    write_json(metadata_path, metadata)
    print(json.dumps({"output": str(output), "metadata": str(metadata_path), "sha256": metadata["sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
