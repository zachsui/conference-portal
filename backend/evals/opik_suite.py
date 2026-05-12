"""Convert the golden dataset into an Opik Dataset + Experiment.

This module gives you two flows:

1. UPLOAD — push every case from ``evals/golden_dataset.json`` into an
   Opik Dataset (default name: ``conference-agent-portal-golden``).
   Items are uploaded idempotently: re-running ``upload`` updates the
   Dataset in place rather than creating duplicates.

2. RUN — run an Opik Experiment against that Dataset. The "task" is a
   real ``POST /agent/chat`` call against the live backend; the
   "metrics" are the same assertion functions used by the local CLI
   runner (``run_eval.py``). Opik renders each case with pass/fail per
   metric and aggregates accuracy in the dashboard.

USAGE
-----
::

    # 1) Make sure the backend is running with Opik creds in .env.
    uvicorn app.main:app --reload --port 8000

    # 2) Push the golden cases into Opik.
    python -m evals.opik_suite upload

    # 3) Run an experiment — every case becomes a trace + scored item.
    python -m evals.opik_suite run

    # 4) Subset:
    python -m evals.opik_suite run --ids TC033,TC037
    python -m evals.opik_suite run --filter prompt_injection --limit 5

NOTES
-----
* The backend store is process-global in-memory. We run with
  ``task_threads=1`` by default so that capacity-fill preconditions in
  one case do not race with another. Use ``--threads N`` to override.
* Each case allocates a fresh attendee and undoes its throwaway
  registrations in a ``finally`` block, so the suite is safe to run
  back-to-back.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    print("ERROR: httpx is required (already a backend dep).", file=sys.stderr)
    sys.exit(2)

try:
    # Pick up OPIK_API_KEY / OPIK_WORKSPACE / GEMINI_API_KEY from
    # backend/.env when invoked as a standalone CLI.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

from evals import run_eval

logger = logging.getLogger("opik_suite")


DEFAULT_DATASET_NAME = "conference-agent-portal-golden"
DEFAULT_EXPERIMENT_PREFIX = "agent-eval"
DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
DEFAULT_BASE_URL = "http://localhost:8000"


# ─────────────────── Dataset shaping ───────────────────
def _build_dataset_item(case: dict[str, Any]) -> dict[str, Any]:
    """Translate a golden_dataset case into an Opik dataset item.

    We keep ``input`` and ``expected_output`` as the two canonical
    columns so the Opik UI renders them nicely side-by-side. Every
    assertion the local runner uses lives under ``expected_output``.
    """
    pre = case.get("preconditions") or {}
    return {
        # Stable per-item key — re-running upload replaces by case_id.
        "case_id": case["id"],
        "category": case["category"],
        "input": {
            "user_input": case["user_input"],
            "setup_messages": pre.get("setup_messages") or [],
            "register_session_ids": pre.get("register_session_ids") or [],
            "make_full_session_ids": pre.get("make_full_session_ids") or [],
        },
        "expected_output": {
            "expected_tools": case.get("expected_tools") or [],
            "expected_order_strict": bool(case.get("expected_order_strict")),
            "must_include_tools": case.get("must_include_tools") or [],
            "forbidden_tools": case.get("forbidden_tools") or [],
            "expected_args": case.get("expected_args") or {},
            "should_call_tools": case.get("should_call_tools", True),
            "should_ask_clarification": bool(case.get("should_ask_clarification")),
            "should_fail_safely": bool(case.get("should_fail_safely")),
            "expected_status": case.get("expected_status") or "any",
            "answer_must_contain": case.get("answer_must_contain") or [],
            "answer_must_not_contain": case.get("answer_must_not_contain") or [],
            "expected_final_behavior": case.get("expected_final_behavior") or "",
        },
        "notes": case.get("notes") or "",
    }


def load_golden_cases(path: Path) -> list[dict[str, Any]]:
    with path.open() as f:
        ds = json.load(f)
    cases = ds.get("test_cases") or []
    if not isinstance(cases, list) or not cases:
        raise RuntimeError(f"No test_cases found in {path}")
    return cases


def filter_cases(
    cases: list[dict[str, Any]],
    only_ids: list[str] | None,
    only_category: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    if only_ids:
        wanted = {x.strip() for x in only_ids}
        cases = [c for c in cases if c["id"] in wanted]
    if only_category:
        cases = [c for c in cases if c["category"] == only_category]
    if limit:
        cases = cases[:limit]
    return cases


# ─────────────────── Upload ───────────────────
def cmd_upload(args: argparse.Namespace) -> int:
    """Push every (filtered) golden case to the Opik Dataset."""
    from agent import opik_io

    if not opik_io.is_enabled():
        print("OPIK_API_KEY is not set; aborting.", file=sys.stderr)
        return 2
    opik_io.ensure_configured()

    import opik

    cases = load_golden_cases(Path(args.dataset_file))
    cases = filter_cases(cases, args.ids_list(), args.filter, args.limit)
    if not cases:
        print("No cases matched the filters; nothing to upload.", file=sys.stderr)
        return 2

    items = [_build_dataset_item(c) for c in cases]

    client = opik.Opik()
    dataset = client.get_or_create_dataset(
        name=args.dataset_name,
        description=(
            "Golden test cases for the Atlas Conference AI assistant. "
            "Pushed from backend/evals/golden_dataset.json."
        ),
    )
    dataset.insert(items)
    opik.flush_tracker(timeout=30)

    print(f"Uploaded {len(items)} item(s) to Opik dataset '{args.dataset_name}'.")
    print("Open the Opik UI → Datasets to inspect, or:")
    print(f"  python -m evals.opik_suite run --dataset-name {args.dataset_name}")
    return 0


# ─────────────────── Metrics ───────────────────
def _build_metrics() -> list:
    """Wrap the existing run_eval check_* functions as Opik metrics.

    Each metric returns 1.0 / 0.0 + a ``reason`` string. The metric is
    marked ``applicable=False`` only when the dataset item has nothing
    to assert against (e.g. no expected_args); we still return 1.0 so
    the case isn't penalized.
    """
    from opik.evaluation.metrics import base_metric, score_result

    BaseMetric = base_metric.BaseMetric
    ScoreResult = score_result.ScoreResult

    def _as_score(name: str, check: run_eval.CheckResult) -> Any:
        if not check.applicable:
            return ScoreResult(name=name, value=1.0, reason="n/a — not applicable")
        return ScoreResult(
            name=name,
            value=1.0 if check.passed else 0.0,
            reason=(check.detail or ("ok" if check.passed else "failed")),
        )

    def _reconstruct_case(expected_output: dict, input_obj: dict) -> dict:
        """Rebuild the dict shape that run_eval.check_* expects."""
        return {
            "expected_tools": expected_output.get("expected_tools") or [],
            "expected_order_strict": expected_output.get("expected_order_strict"),
            "must_include_tools": expected_output.get("must_include_tools") or [],
            "forbidden_tools": expected_output.get("forbidden_tools") or [],
            "expected_args": expected_output.get("expected_args") or {},
            "should_call_tools": expected_output.get("should_call_tools", True),
            "should_ask_clarification": expected_output.get("should_ask_clarification"),
            "should_fail_safely": expected_output.get("should_fail_safely"),
            "expected_status": expected_output.get("expected_status"),
            "answer_must_contain": expected_output.get("answer_must_contain") or [],
            "answer_must_not_contain": (
                expected_output.get("answer_must_not_contain") or []
            ),
            "user_input": (input_obj or {}).get("user_input", ""),
        }

    class _BaseConferenceMetric(BaseMetric):
        """Thin shim: pull `output` (chat response) + `expected_output` (assertions)."""

        check_name: str = ""

        def __init__(self, name: str) -> None:
            super().__init__(name=name)

        def _check(self, case: dict, response: dict, attendee_id: str) -> Any:
            raise NotImplementedError

        def score(
            self,
            *,
            output: dict | None = None,
            expected_output: dict | None = None,
            input: dict | None = None,
            **kwargs: Any,
        ) -> Any:
            output = output or {}
            response = output.get("response") or {}
            attendee_id = output.get("attendee_id") or ""
            case = _reconstruct_case(expected_output or {}, input or {})
            check = self._check(case, response, attendee_id)
            return _as_score(self.name, check)

    class ToolSelectionMetric(_BaseConferenceMetric):
        def __init__(self) -> None:
            super().__init__(name="tool_selection")

        def _check(self, case: dict, response: dict, attendee_id: str) -> Any:
            return run_eval.check_tool_selection(case, response)

    class ToolOrderMetric(_BaseConferenceMetric):
        def __init__(self) -> None:
            super().__init__(name="tool_order")

        def _check(self, case: dict, response: dict, attendee_id: str) -> Any:
            return run_eval.check_tool_order(case, response)

    class ParameterMetric(_BaseConferenceMetric):
        def __init__(self) -> None:
            super().__init__(name="parameter")

        def _check(self, case: dict, response: dict, attendee_id: str) -> Any:
            return run_eval.check_parameters(case, response, attendee_id)

    class ClarificationMetric(_BaseConferenceMetric):
        def __init__(self) -> None:
            super().__init__(name="clarification")

        def _check(self, case: dict, response: dict, attendee_id: str) -> Any:
            return run_eval.check_clarification(case, response)

    class NoToolMetric(_BaseConferenceMetric):
        def __init__(self) -> None:
            super().__init__(name="no_tool")

        def _check(self, case: dict, response: dict, attendee_id: str) -> Any:
            return run_eval.check_no_tool(case, response)

    class SafetyMetric(_BaseConferenceMetric):
        def __init__(self) -> None:
            super().__init__(name="safety")

        def _check(self, case: dict, response: dict, attendee_id: str) -> Any:
            return run_eval.check_safety(case, response)

    class AnswerTextMetric(_BaseConferenceMetric):
        def __init__(self) -> None:
            super().__init__(name="answer_text")

        def _check(self, case: dict, response: dict, attendee_id: str) -> Any:
            return run_eval.check_answer_text(case, response)

    class HallucinationMetric(BaseMetric):
        """1.0 = no hallucination; 0.0 = the agent falsely claimed success."""

        def __init__(self) -> None:
            super().__init__(name="hallucination_safe")

        def score(
            self,
            *,
            output: dict | None = None,
            expected_output: dict | None = None,
            input: dict | None = None,
            **kwargs: Any,
        ) -> Any:
            response = (output or {}).get("response") or {}
            case = _reconstruct_case(expected_output or {}, input or {})
            hallucinated = run_eval.is_hallucination(case, response)
            return ScoreResult(
                name=self.name,
                value=0.0 if hallucinated else 1.0,
                reason=(
                    "answer claims success but no register_session succeeded"
                    if hallucinated
                    else "ok"
                ),
            )

    return [
        ToolSelectionMetric(),
        ToolOrderMetric(),
        ParameterMetric(),
        ClarificationMetric(),
        NoToolMetric(),
        SafetyMetric(),
        AnswerTextMetric(),
        HallucinationMetric(),
    ]


# ─────────────────── Task ───────────────────
def _build_task(api: run_eval.APIClient):
    """Closure that turns a dataset item into a /agent/chat invocation.

    Returns ``{"response": <ChatResponse>, "attendee_id": ...}`` so the
    metrics can read both the tool sequence and the bound attendee.
    """

    def task(item: dict[str, Any]) -> dict[str, Any]:
        input_obj = item.get("input") or {}
        case_id = item.get("case_id") or "TC???"
        # Mirror the local runner's per-case isolation.
        email = f"opik_{case_id}_{uuid.uuid4().hex[:8]}@evals.atlas"
        try:
            attendee_id = api.create_attendee(email=email, name=f"Opik {case_id}")
        except httpx.HTTPError as exc:
            return {
                "response": {
                    "final_answer": "",
                    "status": "failed",
                    "tool_calls": [],
                },
                "attendee_id": "",
                "error": f"create_attendee failed: {exc}",
            }

        # Reshape into the shape setup_case expects.
        preconditions_case = {
            "preconditions": {
                "setup_messages": input_obj.get("setup_messages") or [],
                "register_session_ids": input_obj.get("register_session_ids") or [],
                "make_full_session_ids": input_obj.get("make_full_session_ids") or [],
            }
        }
        throwaway: list[str] = []
        try:
            try:
                throwaway = run_eval.setup_case(api, preconditions_case, attendee_id)
            except httpx.HTTPError as exc:
                return {
                    "response": {
                        "final_answer": "",
                        "status": "failed",
                        "tool_calls": [],
                    },
                    "attendee_id": attendee_id,
                    "error": f"setup failed: {exc}",
                }
            try:
                response = api.chat(attendee_id, input_obj.get("user_input") or "")
            except httpx.HTTPError as exc:
                return {
                    "response": {
                        "final_answer": "",
                        "status": "failed",
                        "tool_calls": [],
                    },
                    "attendee_id": attendee_id,
                    "error": f"chat failed: {exc}",
                }
            return {"response": response, "attendee_id": attendee_id}
        finally:
            run_eval.teardown_case(api, throwaway)

    return task


# ─────────────────── Run ───────────────────
def cmd_run(args: argparse.Namespace) -> int:
    from agent import opik_io

    if not opik_io.is_enabled():
        print("OPIK_API_KEY is not set; aborting.", file=sys.stderr)
        return 2
    opik_io.ensure_configured()

    import opik
    from opik.evaluation import evaluate

    api = run_eval.APIClient(args.base_url)
    if not api.health():
        print(
            f"Backend at {args.base_url}/health is not responding. "
            "Start it with: uvicorn app.main:app --reload --port 8000",
            file=sys.stderr,
        )
        return 2

    client = opik.Opik()
    dataset = client.get_dataset(name=args.dataset_name)
    if dataset is None:
        print(
            f"Dataset '{args.dataset_name}' not found in Opik. "
            f"Run `python -m evals.opik_suite upload` first.",
            file=sys.stderr,
        )
        return 2

    # Item-level filtering: we filter by case_id at the task layer via
    # dataset_filter_string. Opik supports a simple expression syntax,
    # but to keep this portable we instead use nb_samples + post-fetch
    # filter when --ids / --filter is set.
    selected_ids: set[str] | None = None
    if args.ids_list() or args.filter:
        all_items = dataset.get_items()
        wanted_ids = set(args.ids_list() or [])
        chosen = []
        for it in all_items:
            data = it if isinstance(it, dict) else getattr(it, "data", None) or {}
            cid = data.get("case_id")
            cat = data.get("category")
            if wanted_ids and cid not in wanted_ids:
                continue
            if args.filter and cat != args.filter:
                continue
            chosen.append(it.get("id") if isinstance(it, dict) else getattr(it, "id"))
        if args.limit:
            chosen = chosen[: args.limit]
        if not chosen:
            print("No dataset items matched the filters.", file=sys.stderr)
            return 2
        selected_ids = set(filter(None, chosen))

    project = opik_io.project_name()
    metrics = _build_metrics()

    try:
        result = evaluate(
            dataset=dataset,
            task=_build_task(api),
            scoring_metrics=metrics,
            experiment_name_prefix=args.experiment_prefix,
            project_name=project,
            experiment_config={
                "base_url": args.base_url,
                "dataset_name": args.dataset_name,
                "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
            },
            experiment_tags=["golden-eval", "conference-portal"],
            task_threads=args.threads,
            nb_samples=args.limit if not selected_ids else None,
            dataset_item_ids=list(selected_ids) if selected_ids else None,
            verbose=1 if args.verbose else 0,
        )
        opik.flush_tracker(timeout=60)
    finally:
        api.close()

    # Print a compact summary to stdout. Opik already streams URLs to
    # the console; this is just a quick recap.
    print()
    print("=" * 64)
    print("OPIK EXPERIMENT SUBMITTED")
    print("=" * 64)
    print(f"  Project:     {project}")
    print(f"  Dataset:     {args.dataset_name}")
    if hasattr(result, "experiment_name"):
        print(f"  Experiment:  {result.experiment_name}")
    if hasattr(result, "experiment_url"):
        print(f"  URL:         {result.experiment_url}")
    print("Open the Opik UI → Experiments to see per-case pass/fail.")
    return 0


# ─────────────────── CLI ───────────────────
class _Args(argparse.Namespace):
    """argparse.Namespace with a helper to parse comma-separated IDs."""

    ids: str | None = None

    def ids_list(self) -> list[str] | None:
        if not getattr(self, "ids", None):
            return None
        return [x.strip() for x in (self.ids or "").split(",") if x.strip()]


def _add_common_filters(p: argparse.ArgumentParser) -> None:
    p.add_argument("--ids", help="Comma-separated case IDs (e.g. TC033,TC037).")
    p.add_argument("--filter", help="Only cases in this category.")
    p.add_argument("--limit", type=int, help="Stop after N cases.")
    p.add_argument(
        "--dataset-name",
        default=DEFAULT_DATASET_NAME,
        help=f"Opik dataset name (default: {DEFAULT_DATASET_NAME}).",
    )
    p.add_argument(
        "--dataset-file",
        default=str(DATASET_PATH),
        help="Path to golden_dataset.json.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Push the golden dataset to Opik and run experiments.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    upload = sub.add_parser("upload", help="Push golden cases to an Opik Dataset.")
    _add_common_filters(upload)

    run = sub.add_parser("run", help="Run an Opik Experiment over the dataset.")
    _add_common_filters(run)
    run.add_argument("--base-url", default=DEFAULT_BASE_URL)
    run.add_argument(
        "--threads",
        type=int,
        default=1,
        help=(
            "Number of parallel task threads (default 1; backend store "
            "is in-memory, so >1 can race on capacity preconditions)."
        ),
    )
    run.add_argument(
        "--experiment-prefix",
        default=DEFAULT_EXPERIMENT_PREFIX,
        help=f"Opik experiment name prefix (default: {DEFAULT_EXPERIMENT_PREFIX}).",
    )
    run.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args(argv, namespace=_Args())

    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.command == "upload":
        return cmd_upload(args)
    if args.command == "run":
        return cmd_run(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
