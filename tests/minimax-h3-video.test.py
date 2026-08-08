#!/usr/bin/env python3
"""Unit tests for the deterministic MiniMax H3 render contract."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).parents[1] / "tools" / "generate-minimax-h3-video.py"
SPEC = importlib.util.spec_from_file_location("generate_minimax_h3_video", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MiniMaxH3VideoTests(unittest.TestCase):
    def args(self, **overrides):
        values = {
            "width": 1280,
            "height": 736,
            "fps": 24,
            "duration": 15.0,
            "steps": 20,
            "final_width": 1280,
            "final_height": 720,
            "final_duration": 15.0,
            "seed": 20260807,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_fifteen_seconds_aligns_to_h3_frame_grid(self):
        self.assertEqual(MODULE.aligned_frame_count(15.0, 24), 362)
        self.assertEqual(362 % 17, 5)

    def test_exact_720p_acceptance_profile(self):
        self.assertEqual(MODULE.validate_profile(self.args()), 362)
        with self.assertRaisesRegex(ValueError, "exactly 1280x720"):
            MODULE.validate_profile(self.args(final_height=736))
        with self.assertRaisesRegex(ValueError, "1280x736 source"):
            MODULE.validate_profile(self.args(width=864, height=480))
        with self.assertRaisesRegex(ValueError, "full 15-second"):
            MODULE.validate_profile(self.args(duration=5.0))

    def test_final_probe_requires_compatible_video_and_native_stereo_audio(self):
        probe = {
            "format": {"duration": "15.000000"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "pix_fmt": "yuv420p",
                    "width": 1280,
                    "height": 720,
                    "avg_frame_rate": "24/1",
                },
                {"codec_type": "audio", "codec_name": "aac", "channels": 2},
            ],
        }
        MODULE.validate_final_probe(probe, self.args())
        probe["streams"][1]["channels"] = 1
        with self.assertRaisesRegex(RuntimeError, "AAC stereo"):
            MODULE.validate_final_probe(probe, self.args())

    def test_graph_matches_official_sampler_and_native_audio_path(self):
        graph = MODULE.build_prompt_graph("integrated_multimodal_description: test", self.args(), 362)
        self.assertEqual(graph["8"]["inputs"]["sampler_name"], "res_multistep")
        self.assertEqual(graph["9"]["inputs"]["steps"], 20)
        self.assertEqual(graph["5"]["inputs"]["length"], 362)
        self.assertEqual(graph["13"]["inputs"]["audio"], ["12", 0])
        self.assertEqual(graph["14"]["inputs"]["codec"]["codec"], "h264")

    def test_model_pins_are_complete(self):
        self.assertEqual(len(MODULE.MODEL_REVISION), 40)
        self.assertEqual(len(MODULE.COMFY_COMMIT), 40)
        self.assertEqual(len(MODULE.MODEL_FILES), 4)
        self.assertTrue(all(len(value["sha256"]) == 64 for value in MODULE.MODEL_FILES.values()))


if __name__ == "__main__":
    unittest.main()
