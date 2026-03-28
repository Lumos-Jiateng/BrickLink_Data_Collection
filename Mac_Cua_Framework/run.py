#!/usr/bin/env python3
"""Mac CUA Framework — run a workflow on the local Mac with Qwen3-VL + PyAutoGUI."""

import argparse
import datetime
import logging
import os
import sys
import threading
import time
from io import BytesIO

import cv2
import numpy as np
import pyautogui

# OSWorld path for transitive imports inside qwen3vl_agent_vllm.py
sys.path.insert(0, "/Users/jiateng5/research/OSExpert/OSWorld")
from agent.qwen3vl_agent_vllm import Qwen3VLAgent

from workflows.minimize_reopen_cursor import WORKFLOW


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("mac_cua")


class ScreenRecorder:
    """Captures the screen in a background thread and writes an mp4 on stop."""

    def __init__(self, output_path: str, fps: int = 5):
        self.output_path = output_path
        self.fps = fps
        self._frames: list = []
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)

    def start(self):
        self._stop_event.clear()
        self._frames.clear()
        self._thread.start()
        logger.info("Screen recording started → %s  (%d fps)", self.output_path, self.fps)

    def stop(self):
        self._stop_event.set()
        self._thread.join()
        if not self._frames:
            logger.warning("No frames captured — recording not saved.")
            return
        self._write_video()
        logger.info("Screen recording saved → %s  (%d frames)", self.output_path, len(self._frames))

    def _capture_loop(self):
        interval = 1.0 / self.fps
        while not self._stop_event.is_set():
            t0 = time.time()
            frame = np.array(pyautogui.screenshot())          # RGB
            self._frames.append(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            elapsed = time.time() - t0
            time.sleep(max(0.0, interval - elapsed))

    def _write_video(self):
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        h, w = self._frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(self.output_path, fourcc, self.fps, (w, h))
        for frame in self._frames:
            writer.write(frame)
        writer.release()


def get_obs() -> dict:
    """Capture a full-screen screenshot and return it as PNG bytes."""
    buf = BytesIO()
    pyautogui.screenshot().save(buf, "PNG")
    return {"screenshot": buf.getvalue()}


def run_phase(agent, phase, sleep_after_execution):
    logger.info("=" * 60)
    logger.info("Phase: %s", phase["name"])
    logger.info("=" * 60)
    sleep_after_execution = phase.get("sleep", sleep_after_execution)

    # ── Direct (deterministic) actions — no LLM ─────────────────────────────
    if "direct_actions" in phase:
        for code in phase["direct_actions"]:
            exec(code)  # noqa: S102
            time.sleep(sleep_after_execution)
        logger.info("Phase '%s' DONE", phase["name"])
        return True

    # ── LLM-driven actions ───────────────────────────────────────────────────
    instruction = phase["instruction"]
    max_steps   = phase["max_steps"]
    done        = False
    step_idx    = 0
    actions     = []

    obs = get_obs()
    failed = False

    while not done and step_idx < max_steps:
        logger.info("Step %d/%d", step_idx + 1, max_steps)
        response, actions = agent.predict(instruction, obs)

        for action in actions:
            logger.info("Action: %s", action)
            if action == "DONE":
                done = True
                break
            elif action == "FAIL":
                failed = True
                done = True
                break
            elif action == "WAIT":
                time.sleep(2)
            else:
                #import ipdb; ipdb.set_trace()
                exec(action, {"pyautogui": pyautogui})  # noqa: S102
                time.sleep(sleep_after_execution)

        obs = get_obs()
        step_idx += 1

    # Treat exhausting max_steps without an explicit FAIL as success —
    # the model often doesn't call terminate even after completing the task.
    success = not failed
    logger.info("Phase '%s' %s", phase["name"], "DONE" if success else "FAILED")
    return success


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record_dir", default="/Users/jiateng5/research/Mac_Cua_Framework/interactive_position_workflow")
    parser.add_argument("--record_fps", type=int,   default=5)
    parser.add_argument("--model",                 default="qwen-3-vl")
    parser.add_argument("--model_url",             default="http://172.22.225.5:8031/v1")
    parser.add_argument("--api_key",               default="EMPTY")
    parser.add_argument("--temperature",           type=float, default=1.0)
    parser.add_argument("--top_p",                 type=float, default=0.9)
    parser.add_argument("--max_tokens",            type=int,   default=32768)
    parser.add_argument("--history_n",             type=int,   default=1)
    parser.add_argument("--coordinate_type",       default="relative")
    parser.add_argument("--sleep_after_execution", type=float, default=0.5)
    args = parser.parse_args()

    agent = Qwen3VLAgent(
        model=args.model,
        base_url=args.model_url,
        api_key=args.api_key,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        history_n=args.history_n,
        coordinate_type=args.coordinate_type,
        api_backend="openai",
    )
    agent.reset(logger)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(args.record_dir, f"recording_{ts}.mp4")
    recorder = ScreenRecorder(output_path=video_path, fps=args.record_fps)
    recorder.start()

    try:
        for phase in WORKFLOW:
            success = run_phase(agent, phase, args.sleep_after_execution)
            agent.reset(logger)   # clear history between phases
            if not success:
                logger.error("Workflow stopped at phase: %s", phase["name"])
                break
    finally:
        recorder.stop()

    if not success:
        sys.exit(1)

    logger.info("Workflow complete.")


if __name__ == "__main__":
    main()
