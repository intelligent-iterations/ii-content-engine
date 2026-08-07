# MiniMax H3 Video Prompting

Use this profile for local MiniMax H3 text-to-video generation with native
stereo audio. The reusable showcase is
[`prompts/minimax-h3-showcase.json`](../../prompts/minimax-h3-showcase.json).

## Prompt contract

Write the prompt in three explicit sections:

1. `integrated_multimodal_description`: establish the whole visual language,
   then describe numbered shots. Start later shots with an exact timestamp,
   such as `[Shot 2] At 00:05.000`. Name the camera move, subject action,
   lighting, material behavior, and continuity constraints.
2. `overall_soundscape`: direct stereo ambience and synchronized sound effects.
   State `No voices or speech` when visible lip sync is not required.
3. `non_diegetic_music`: describe the score and its timed changes separately
   from sounds that exist inside the scene.

Keep one recognizable hero subject across cuts. Prefer three strong five-second
beats over many short, unrelated images. Do not ask the model to spell titles,
captions, or logos; exact text belongs in deterministic post-production.

## Pinned local quality profile

- Open weights: `Comfy-Org/MiniMax-H3` at commit
  `eb8a16107c595128b3a578f82d2ce2f75920c355`.
- ComfyUI: `531ea7db139a856a830182694441e9755f0e260a`.
- Official pruned INT8 ConvRot diffusion model and NVFP4-AWQ Qwen3-VL text
  encoder; all four model files have fixed byte counts and SHA256 digests.
- Source: 1280x736, 362 frames, 24 fps, 20 `res_multistep` sampling steps.
- Delivery: center-crop without upscaling, encode H.264/AAC, and trim to exact
  1280x720 at 15.000 seconds with stereo audio.

The source frame count follows H3's `17k+5` grid. Fifteen seconds at 24 fps
therefore renders 362 frames (15.083 seconds) before the acceptance transcode
trims the result to exactly 15 seconds.

## Acceptance

Generation success alone is not acceptance. The renderer must retain the raw
clip, direct prompt, executable API graph, model and ComfyUI pins, hashes, and
FFprobe data. The final gate requires 1280x720, 24 fps, 15.000 seconds, H.264
video, and two-channel audio. A run with missing speech constraints, missing
audio, unexpected dimensions, or an unverified model file fails closed.
