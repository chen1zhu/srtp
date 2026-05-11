"""
Automated multi-model benchmark described in `backend/tests/plan.md`.

Scenarios:
- single_turn: one user message asking for 09:00-15:30 start-point clustering with self-adjusted k (max 5 iterations).
- multi_turn: three-step dialogue where the user gradually adds constraints and requests artifacts.

Outputs:
- A JSON log in `backend/tests/model_return/<timestamp>_model_benchmark.json` capturing prompts, answers, timing, and generated files per model.
- Log schema (per model):
  {
    "model_id": str,
    "status": "success" | "error",
    "single_turn": {...}?,
    "multi_turn": {...}?,
    "errors": [str]
  }

Usage:
    python backend/tests/model_benchmark.py
    python backend/tests/model_benchmark.py --models deepseek/deepseek-v3.2,openai/gpt-5.1 --scenarios single

Assumptions:
- `DEEPSEEK_API_KEY` is set for OpenRouter access.
- Test file exists at `uploads/20200101_binjiang_point.xlsx` (copied from sample uploads).
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend import deepseek_agent

# Model set from plan.md
MODEL_IDS = [
    "deepseek/deepseek-v3.2",
    "openai/gpt-5.1",
    "meta-llama/llama-3.1-8b-instruct",
    "meta-llama/llama-3.1-70b-instruct",
    "qwen/qwen3-235b-a22b-2507",
]

UPLOAD_FILENAME = "20200101_binjiang_point.xlsx"
BASE_URL = "https://openrouter.ai/api/v1"
SINGLE_TURN_PROMPT = (
    "请对文件 uploads/20200101_binjiang_point.xlsx 中时间段上午九点到下午三点半的起点数据进行聚类分析，"
    "但是由于我当前并不清楚数据的特点，所以请你自行设定一个初始聚类数目，并根据生成结果进行判断，"
    "若你觉得不合适则用新的聚类数目再次生成新的结果；循环往复直到你认为结果可以有一定依据或者循环次数达到5次。"
)
MULTI_TURN_PROMPTS = [
    "我上传了 uploads/20200101_binjiang_point.xlsx，其中有出租车轨迹数据。先请你确认文件字段含义、可做的分析方向，"
    "以及你在运行前需要我补充的内容。",
    "本次关注上午09:00到下午15:30的起点数据。请先任选一个合理的初始聚类数目，跑出第一次结果；"
    "如果聚类质量一般，请调整聚类数继续，最多 5 轮。每轮说明理由和是否继续。",
    "请给出最终选择的聚类数、每个簇的规模与中心点、质量判断，并导出聚类的 shp/可视化图片。"
    "若生成了文件，把可下载路径列出。",
]

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
LOG_DIR = CURRENT_DIR / "model_return"


def _ensure_upload() -> Path:
    uploads_path = REPO_ROOT / "uploads" / UPLOAD_FILENAME
    if not uploads_path.exists():
        raise FileNotFoundError(f"Test file not found: {uploads_path}")
    return uploads_path


def _set_model_temporarily(model_id: str):
    """Context manager-like helper to swap model id safely."""

    class _ModelGuard:
        def __enter__(self) -> None:
            self.original = deepseek_agent.DEFAULT_MODEL_NAME
            deepseek_agent.DEFAULT_MODEL_NAME = model_id

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
            deepseek_agent.DEFAULT_MODEL_NAME = getattr(self, "original", deepseek_agent.DEFAULT_MODEL_NAME)

    return _ModelGuard()


def _run_agent(
    model_id: str,
    prompt: str,
    messages: Optional[List[Dict[str, Any]]],
    session_files: Optional[List[str]],
) -> Dict[str, Any]:
    with _set_model_temporarily(model_id):
        return deepseek_agent.run_agent_conversation(
            user_prompt=prompt,
            messages=messages,
            session_generated_files=session_files,
        )


def run_single_turn(model_id: str) -> Dict[str, Any]:
    session_files: List[str] = []
    start = time.perf_counter()
    try:
        result = _run_agent(model_id, SINGLE_TURN_PROMPT, None, session_files)
        duration = time.perf_counter() - start
        return {
            "status": "success",
            "prompt": SINGLE_TURN_PROMPT,
            "answer": result.get("answer"),
            "requires_follow_up": result.get("requires_follow_up"),
            "generated_files": result.get("generated_files", []),
            "messages_seen": len(result.get("messages", [])),
            "latency_seconds": round(duration, 3),
        }
    except Exception as exc:  # noqa: BLE001
        duration = time.perf_counter() - start
        return {
            "status": "error",
            "prompt": SINGLE_TURN_PROMPT,
            "error": str(exc),
            "latency_seconds": round(duration, 3),
        }


def run_multi_turn(model_id: str) -> Dict[str, Any]:
    messages: Optional[List[Dict[str, Any]]] = None
    session_files: List[str] = []
    turns: List[Dict[str, Any]] = []
    status = "success"
    error: Optional[str] = None
    start = time.perf_counter()

    try:
        for idx, prompt in enumerate(MULTI_TURN_PROMPTS, start=1):
            partial = _run_agent(model_id, prompt, messages, session_files)
            messages = partial.get("messages")
            session_files = partial.get("generated_files", session_files)
            turns.append(
                {
                    "turn": idx,
                    "prompt": prompt,
                    "answer": partial.get("answer"),
                    "requires_follow_up": partial.get("requires_follow_up"),
                    "generated_files": partial.get("generated_files", []),
                    "messages_seen": len(partial.get("messages", [])),
                }
            )
    except Exception as exc:  # noqa: BLE001
        status = "error"
        error = str(exc)

    duration = time.perf_counter() - start
    return {
        "status": status,
        "turns": turns,
        "final_answer": turns[-1]["answer"] if turns else None,
        "generated_files": session_files,
        "latency_seconds": round(duration, 3),
        "error": error,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run automated model comparisons defined in tests/plan.md")
    parser.add_argument(
        "--models",
        help="Comma separated model ids; defaults to plan.md list.",
        default=None,
    )
    parser.add_argument(
        "--scenarios",
        choices=["single", "multi", "both"],
        default="both",
        help="Which scenarios to run.",
    )
    parser.add_argument(
        "--output",
        help="Custom output json path. Defaults to model_return/<timestamp>_model_benchmark.json",
        default=None,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_models = MODEL_IDS if not args.models else [m.strip() for m in args.models.split(",") if m.strip()]
    if not selected_models:
        raise ValueError("No models specified")

    run_id = str(uuid.uuid4())
    batch_start = datetime.utcnow().isoformat() + "Z"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    output_path = (
        Path(args.output)
        if args.output
        else LOG_DIR / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_model_benchmark.json"
    )

    # Validate upload presence early to fail fast.
    uploads_path = _ensure_upload()

    log: Dict[str, Any] = {
        "run_id": run_id,
        "batch_started_at": batch_start,
        "batch_finished_at": None,
        "base_url": BASE_URL,
        "upload_file": str(uploads_path),
        "models": [],
    }

    for model_id in selected_models:
        model_entry: Dict[str, Any] = {
            "model_id": model_id,
            "status": "success",
            "errors": [],
        }

        if args.scenarios in ("single", "both"):
            single = run_single_turn(model_id)
            model_entry["single_turn"] = single
            if single.get("status") == "error":
                model_entry["status"] = "error"
                model_entry["errors"].append(f"single_turn: {single.get('error')}")

        if args.scenarios in ("multi", "both"):
            multi = run_multi_turn(model_id)
            model_entry["multi_turn"] = multi
            if multi.get("status") == "error":
                model_entry["status"] = "error"
                if multi.get("error"):
                    model_entry["errors"].append(f"multi_turn: {multi['error']}")

        log["models"].append(model_entry)

    log["batch_finished_at"] = datetime.utcnow().isoformat() + "Z"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"Run {run_id} finished. Log saved to {output_path}")


if __name__ == "__main__":
    main()
