"""Automated evaluation runner for the Conference AI Assistant.

Loads backend/evals/golden_dataset.json, replays each test case against
the live POST /agent/chat endpoint, and computes accuracy metrics for
tool selection, ordering, parameters, safety, and hallucination
prevention.

USAGE
-----
1. Start the backend in another terminal:
       uvicorn app.main:app --reload --port 8000
2. From the `backend/` directory with the venv active:

       python -m evals.run_eval                         # full run
       python -m evals.run_eval --filter session_search
       python -m evals.run_eval --ids TC033,TC037       # deterministic-only
       python -m evals.run_eval --opik              # also log each case to Opik
       python -m evals.run_eval --sleep 8               # pace Gemini RPM
       python -m evals.run_eval --base-url http://localhost:8001

CAVEATS
-------
* Gemini free tier has a daily request cap (~20 RPD on
  gemini-3.1-flash-lite). The dataset's confirmation short-circuit cases
  (`yes` / `no`) consume ZERO LLM calls, but each other case typically
  costs 1–3 calls. Use --filter / --ids / --limit to budget runs.
* Each test creates a fresh attendee_id (so pending_action and prior
  registrations never leak across cases). Throwaway registrations made
  to fill capacity are cleaned up in a `finally` block after the case.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    print(
        "ERROR: httpx is required. Install with `pip install httpx` "
        "(it is already a transitive dep of FastAPI/google-genai, so "
        "activating the backend venv should be enough).",
        file=sys.stderr,
    )
    sys.exit(2)


DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
DEFAULT_REPORT_PATH = Path(__file__).parent / "eval_report.json"
DEFAULT_BASE_URL = "http://localhost:8000"

# Phrases that count as a "success claim" in the assistant's reply.
# Used by the hallucination detector when no successful register_session
# call actually fired.
SUCCESS_CLAIM_PATTERNS = [
    r"you('?re| are) (now )?registered",
    r"i('?ve| have)? registered you",
    r"i('?ve| have)? signed you up",
    r"successfully registered",
    r"registration (is )?confirmed",
    r"you'?re all set for",
    r"booked you (into|for)",
]
SUCCESS_CLAIM_RE = re.compile("|".join(SUCCESS_CLAIM_PATTERNS), re.IGNORECASE)


logger = logging.getLogger("eval_runner")


# ─────────────────── Data structures ───────────────────
@dataclass
class CheckResult:
    """Outcome of a single named assertion within a test case."""

    name: str
    applicable: bool
    passed: bool
    detail: str = ""


@dataclass
class CaseResult:
    """Full per-case record (input + actual response + checks)."""

    id: str
    category: str
    passed: bool
    error: str | None = None
    request: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] = field(default_factory=dict)
    checks: list[CheckResult] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "passed": self.passed,
            "error": self.error,
            "request": self.request,
            "response": self.response,
            "failures": self.failures,
            "checks": [
                {
                    "name": c.name,
                    "applicable": c.applicable,
                    "passed": c.passed,
                    "detail": c.detail,
                }
                for c in self.checks
            ],
        }


# ─────────────────── HTTP helpers ───────────────────
class APIClient:
    """Thin wrapper around the backend HTTP surface used by the runner."""

    def __init__(self, base_url: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self.client.close()

    def health(self) -> bool:
        try:
            r = self.client.get("/health", timeout=5.0)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    def create_attendee(self, email: str, name: str) -> str:
        r = self.client.post(
            "/attendees",
            json={"email": email, "name": name},
        )
        r.raise_for_status()
        return r.json()["attendee_id"]

    def get_capacity(self, session_id: str) -> dict[str, Any]:
        r = self.client.get(f"/sessions/{session_id}/capacity")
        r.raise_for_status()
        return r.json()

    def register(self, attendee_id: str, session_id: str) -> dict[str, Any]:
        r = self.client.post(
            "/registrations",
            json={"attendee_id": attendee_id, "session_id": session_id},
        )
        r.raise_for_status()
        return r.json()

    def cancel(self, registration_id: str) -> None:
        r = self.client.delete(f"/registrations/{registration_id}")
        if r.status_code not in (204, 404):
            r.raise_for_status()

    def chat(self, attendee_id: str, message: str) -> dict[str, Any]:
        r = self.client.post(
            "/agent/chat",
            json={"attendee_id": attendee_id, "message": message},
            timeout=120.0,
        )
        r.raise_for_status()
        return r.json()


# ─────────────────── Precondition setup ───────────────────
def setup_case(
    api: APIClient, case: dict[str, Any], attendee_id: str
) -> list[str]:
    """Apply preconditions; return list of throwaway registration_ids to undo."""
    pre = case.get("preconditions") or {}
    throwaway_reg_ids: list[str] = []

    # 1) Fill sessions to capacity using throwaway attendees.
    for sid in pre.get("make_full_session_ids") or []:
        cap = api.get_capacity(sid)
        seats_left = int(cap.get("seats_remaining", 0))
        for _ in range(seats_left):
            email = f"fill_{sid}_{uuid.uuid4().hex[:8]}@evals.atlas"
            fa_id = api.create_attendee(email=email, name="Eval Filler")
            try:
                reg = api.register(fa_id, sid)
                throwaway_reg_ids.append(reg["registration_id"])
            except httpx.HTTPStatusError:
                break  # already full, stop

    # 2) Pre-register the *test* attendee for these sessions (sets up
    #    schedule conflicts or "already registered" duplicates).
    for sid in pre.get("register_session_ids") or []:
        try:
            api.register(attendee_id, sid)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Precondition register failed for %s on %s: %s",
                attendee_id,
                sid,
                exc,
            )

    # 3) Replay setup_messages as chat turns (these establish
    #    pending_action for confirmation cases).
    for msg in pre.get("setup_messages") or []:
        api.chat(attendee_id, msg)

    return throwaway_reg_ids


def teardown_case(api: APIClient, throwaway_reg_ids: list[str]) -> None:
    for rid in throwaway_reg_ids:
        try:
            api.cancel(rid)
        except httpx.HTTPError:
            pass


# ─────────────────── Assertion logic ───────────────────
def is_subsequence(expected: list[str], actual: list[str]) -> bool:
    """Does `expected` appear in `actual` in order (with arbitrary gaps)?"""
    it = iter(actual)
    return all(e in it for e in expected)


def tool_call_names(response: dict[str, Any]) -> list[str]:
    return [tc["tool_name"] for tc in response.get("tool_calls", [])]


def find_calls(response: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return [tc for tc in response.get("tool_calls", []) if tc["tool_name"] == name]


def successful_register_in(response: dict[str, Any]) -> bool:
    for tc in response.get("tool_calls", []):
        if tc["tool_name"] != "register_session":
            continue
        result = tc.get("result") or {}
        if tc.get("success") and isinstance(result, dict) and result.get("ok"):
            return True
    return False


def check_tool_selection(case: dict[str, Any], response: dict[str, Any]) -> CheckResult:
    """Did expected_tools appear (as subsequence) AND no forbidden tools fire?"""
    actual = tool_call_names(response)
    expected = case.get("expected_tools") or []
    must_include = case.get("must_include_tools") or []
    forbidden = case.get("forbidden_tools") or []

    problems: list[str] = []
    if expected and not is_subsequence(expected, actual):
        problems.append(
            f"expected_tools {expected} not present as subsequence in {actual}"
        )
    missing = [t for t in must_include if t not in actual]
    if missing:
        problems.append(f"missing required tool calls: {missing}")
    blocked = [t for t in forbidden if t in actual]
    if blocked:
        problems.append(f"forbidden tool calls fired: {blocked}")

    applicable = bool(expected or must_include or forbidden)
    return CheckResult(
        name="tool_selection",
        applicable=applicable,
        passed=not problems,
        detail="; ".join(problems),
    )


def check_tool_order(case: dict[str, Any], response: dict[str, Any]) -> CheckResult:
    """If expected_order_strict, names must equal expected_tools exactly."""
    if not case.get("expected_order_strict"):
        return CheckResult(name="tool_order", applicable=False, passed=True)
    expected = case.get("expected_tools") or []
    actual = tool_call_names(response)
    passed = expected == actual
    return CheckResult(
        name="tool_order",
        applicable=True,
        passed=passed,
        detail="" if passed else f"expected {expected}, got {actual}",
    )


def check_parameters(
    case: dict[str, Any], response: dict[str, Any], attendee_id: str
) -> CheckResult:
    """Validate per-tool argument constraints (partial match)."""
    expected_args = case.get("expected_args") or {}
    if not expected_args:
        return CheckResult(name="parameter", applicable=False, passed=True)

    problems: list[str] = []
    for tool, constraints in expected_args.items():
        calls = find_calls(response, tool)
        if not calls:
            # If the tool wasn't called, we can't fail on params — that's
            # a tool_selection issue, recorded separately.
            continue
        ok_any = False
        for call in calls:
            args = call.get("arguments") or {}
            if all(
                _arg_matches(args.get(k), v, k, attendee_id)
                for k, v in constraints.items()
            ):
                ok_any = True
                break
        if not ok_any:
            problems.append(
                f"{tool} called but none of its calls satisfy {constraints}; "
                f"actual args: {[c.get('arguments') for c in calls]}"
            )

    return CheckResult(
        name="parameter",
        applicable=True,
        passed=not problems,
        detail="; ".join(problems),
    )


def _arg_matches(actual: Any, expected: Any, key: str, attendee_id: str) -> bool:
    """attendee_id is always bound to the request's attendee, so we
    compare against that rather than the literal dataset value."""
    if key == "attendee_id":
        return actual == attendee_id
    return actual == expected


def check_clarification(case: dict[str, Any], response: dict[str, Any]) -> CheckResult:
    expected = case.get("should_ask_clarification")
    expected_status = case.get("expected_status")
    if not expected and expected_status != "clarification_needed":
        return CheckResult(name="clarification", applicable=False, passed=True)

    actual_status = response.get("status")
    if expected and actual_status == "clarification_needed":
        return CheckResult(name="clarification", applicable=True, passed=True)
    if expected_status and actual_status == expected_status:
        return CheckResult(name="clarification", applicable=True, passed=True)

    return CheckResult(
        name="clarification",
        applicable=True,
        passed=False,
        detail=f"expected clarification_needed, got status={actual_status}",
    )


def check_no_tool(case: dict[str, Any], response: dict[str, Any]) -> CheckResult:
    if case.get("should_call_tools") is not False:
        return CheckResult(name="no_tool", applicable=False, passed=True)
    calls = tool_call_names(response)
    if not calls:
        return CheckResult(name="no_tool", applicable=True, passed=True)
    # Soft pass: still passes if all calls are non-mutating reads.
    allowed_reads = {"search_sessions", "get_session_detail", "get_agenda"}
    if all(c in allowed_reads for c in calls):
        return CheckResult(
            name="no_tool",
            applicable=True,
            passed=True,
            detail=f"non-mutating tool reads only: {calls}",
        )
    return CheckResult(
        name="no_tool",
        applicable=True,
        passed=False,
        detail=f"expected no tool calls but got {calls}",
    )


def check_safety(case: dict[str, Any], response: dict[str, Any]) -> CheckResult:
    """For should_fail_safely cases: no successful register and no false success."""
    if not case.get("should_fail_safely"):
        return CheckResult(name="safety", applicable=False, passed=True)

    answer = (response.get("final_answer") or "").lower()
    successful = successful_register_in(response)
    claims_success = bool(SUCCESS_CLAIM_RE.search(answer))

    problems: list[str] = []
    if successful:
        problems.append("register_session succeeded but the case expected a failure path")
    if claims_success and not successful:
        problems.append("answer claims success even though register did not succeed")

    # answer_must_not_contain is also enforced (extra guard).
    for phrase in case.get("answer_must_not_contain") or []:
        if phrase.lower() in answer:
            problems.append(f"answer contains forbidden phrase: {phrase!r}")

    return CheckResult(
        name="safety",
        applicable=True,
        passed=not problems,
        detail="; ".join(problems),
    )


def check_answer_text(case: dict[str, Any], response: dict[str, Any]) -> CheckResult:
    """answer_must_contain / answer_must_not_contain (always applicable when present)."""
    must = case.get("answer_must_contain") or []
    must_not = case.get("answer_must_not_contain") or []
    if not must and not must_not:
        return CheckResult(name="answer_text", applicable=False, passed=True)

    answer = (response.get("final_answer") or "").lower()
    problems = []
    for phrase in must:
        if phrase.lower() not in answer:
            problems.append(f"answer missing required phrase: {phrase!r}")
    for phrase in must_not:
        if phrase.lower() in answer:
            problems.append(f"answer contains forbidden phrase: {phrase!r}")
    return CheckResult(
        name="answer_text",
        applicable=True,
        passed=not problems,
        detail="; ".join(problems),
    )


def is_hallucination(case: dict[str, Any], response: dict[str, Any]) -> bool:
    """Did the agent claim success when no register actually succeeded?"""
    if successful_register_in(response):
        return False
    answer = response.get("final_answer") or ""
    return bool(SUCCESS_CLAIM_RE.search(answer))


# ─────────────────── Per-case execution ───────────────────
def run_case(api: APIClient, case: dict[str, Any]) -> CaseResult:
    case_id = case["id"]
    category = case["category"]
    result = CaseResult(id=case_id, category=category, passed=False)

    # Fresh attendee per case.
    email = f"eval_{case_id}_{uuid.uuid4().hex[:8]}@evals.atlas"
    try:
        attendee_id = api.create_attendee(email=email, name=f"Eval {case_id}")
    except httpx.HTTPError as exc:
        result.error = f"Could not create test attendee: {exc}"
        return result

    throwaway: list[str] = []
    try:
        try:
            throwaway = setup_case(api, case, attendee_id)
        except httpx.HTTPError as exc:
            result.error = f"Precondition setup failed: {exc}"
            return result

        # Actual chat call.
        result.request = {
            "attendee_id": attendee_id,
            "message": case["user_input"],
        }
        try:
            response = api.chat(attendee_id, case["user_input"])
        except httpx.HTTPError as exc:
            result.error = f"chat call failed: {exc}"
            return result
        result.response = response

        # Run all assertions.
        checks = [
            check_tool_selection(case, response),
            check_tool_order(case, response),
            check_parameters(case, response, attendee_id),
            check_clarification(case, response),
            check_no_tool(case, response),
            check_safety(case, response),
            check_answer_text(case, response),
        ]
        result.checks = checks

        failures = [
            f"[{c.name}] {c.detail or 'failed'}"
            for c in checks
            if c.applicable and not c.passed
        ]
        if is_hallucination(case, response):
            failures.append("[hallucination] answer claims success but no register_session succeeded")
        result.failures = failures
        result.passed = len(failures) == 0
        return result

    finally:
        teardown_case(api, throwaway)


# ─────────────────── Aggregate metrics ───────────────────
def aggregate_metrics(results: list[CaseResult]) -> dict[str, Any]:
    def ratio(name: str, predicate=lambda c: c.applicable) -> dict[str, Any]:
        applicable = []
        passed = []
        for r in results:
            for c in r.checks:
                if c.name == name and predicate(c):
                    applicable.append(r.id)
                    if c.passed:
                        passed.append(r.id)
        total = len(applicable)
        return {
            "passed": len(passed),
            "applicable": total,
            "accuracy": round(len(passed) / total, 4) if total else None,
        }

    halluc = [r for r in results if is_hallucination_from_result(r)]
    total = len(results)

    return {
        "tool_selection_accuracy": ratio("tool_selection"),
        "tool_order_accuracy": ratio("tool_order"),
        "parameter_accuracy": ratio("parameter"),
        "clarification_accuracy": ratio("clarification"),
        "no_tool_accuracy": ratio("no_tool"),
        "safety_accuracy": ratio("safety"),
        "hallucination_failure_rate": {
            "hallucinations": len(halluc),
            "total_cases": total,
            "rate": round(len(halluc) / total, 4) if total else None,
            "cases": [r.id for r in halluc],
        },
    }


def is_hallucination_from_result(r: CaseResult) -> bool:
    return any(f.startswith("[hallucination]") for f in r.failures)


# ─────────────────── Reporting ───────────────────
def color(text: str, code: str, enabled: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if enabled else text


def print_case_line(r: CaseResult, color_enabled: bool) -> None:
    status = "PASS" if r.passed else ("ERROR" if r.error else "FAIL")
    status_color = "32" if r.passed else ("33" if r.error else "31")
    tag = color(status.ljust(5), status_color, color_enabled)
    tools = ",".join(tool_call_names(r.response)) or "—"
    print(f"  {r.id:6}  [{r.category:30s}]  {tag}   tools=[{tools}]")
    if r.error:
        print(f"         └─ error: {r.error}")
    for f in r.failures:
        print(f"         └─ {f}")


def print_summary(
    results: list[CaseResult],
    metrics: dict[str, Any],
    elapsed: float,
    color_enabled: bool,
) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    errored = sum(1 for r in results if r.error)
    failed = total - passed - errored

    bar = "=" * 64
    print()
    print(bar)
    print("EVAL SUMMARY")
    print(bar)
    print(f"Total cases:    {total}")
    print(f"  Passed:       {color(str(passed), '32', color_enabled)}")
    print(f"  Failed:       {color(str(failed), '31', color_enabled)}")
    print(f"  Errored:      {color(str(errored), '33', color_enabled)}")
    print(f"  Elapsed:      {elapsed:.1f}s")
    print()
    print("Metric breakdown")
    print("-" * 64)
    for name in (
        "tool_selection_accuracy",
        "tool_order_accuracy",
        "parameter_accuracy",
        "clarification_accuracy",
        "no_tool_accuracy",
        "safety_accuracy",
    ):
        m = metrics[name]
        if m["applicable"] == 0:
            line = f"  {name:30s}  n/a (no applicable cases)"
        else:
            pct = (m["passed"] / m["applicable"]) * 100
            line = f"  {name:30s}  {m['passed']:>3}/{m['applicable']:<3}  ({pct:5.1f}%)"
        print(line)
    halluc = metrics["hallucination_failure_rate"]
    rate_pct = (halluc["rate"] or 0.0) * 100
    print(
        f"  {'hallucination_failure_rate':30s}  "
        f"{halluc['hallucinations']:>3}/{halluc['total_cases']:<3}  ({rate_pct:5.1f}%)   "
        f"{'  ← lower is better' if halluc['hallucinations'] else ''}"
    )
    if halluc["cases"]:
        print(f"        offenders: {halluc['cases']}")
    print(bar)


def save_report(
    path: Path,
    base_url: str,
    results: list[CaseResult],
    metrics: dict[str, Any],
    elapsed: float,
) -> None:
    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "elapsed_seconds": round(elapsed, 2),
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed and not r.error),
            "errored": sum(1 for r in results if r.error),
            "metrics": metrics,
        },
        "results": [r.to_dict() for r in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Detailed report written to {path}")


def log_opik_golden_case(case: dict[str, Any], result: CaseResult) -> None:
    """Push one golden-eval case as a standalone Opik trace (dashboard view)."""
    if not os.getenv("OPIK_API_KEY", "").strip():
        logger.warning("--opik was passed but OPIK_API_KEY is unset; skipping Opik")
        return
    try:
        from agent import opik_io

        opik_io.ensure_configured()
        import opik

        client = opik.Opik()
        tr = client.trace(
            name=f"golden_eval:{case['id']}",
            input={
                "user_input": case["user_input"],
                "category": case["category"],
            },
            metadata={
                "golden_case_id": case["id"],
                "passed": result.passed,
            },
            project_name=opik_io.project_name(),
            tags=["golden-eval", case.get("category", "unknown")],
        )
        resp = result.response or {}
        output: dict[str, Any] = {
            "passed": result.passed,
            "failures": result.failures,
            "assistant_status": resp.get("status"),
            "tool_sequence": [
                tc.get("tool_name") for tc in resp.get("tool_calls", [])
            ],
            "final_answer_preview": (resp.get("final_answer") or "")[:500],
        }
        err_info: dict[str, Any] | None = None
        if result.error:
            err_info = {"message": result.error}
        tr.end(output=output, error_info=err_info)
        opik.flush_tracker(timeout=20)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Opik golden-eval log failed: %s", exc)


# ─────────────────── Main ───────────────────
def filter_cases(
    all_cases: list[dict[str, Any]],
    only_ids: list[str] | None,
    only_category: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    cases = all_cases
    if only_ids:
        wanted = {tid.strip() for tid in only_ids}
        cases = [c for c in cases if c["id"] in wanted]
    if only_category:
        cases = [c for c in cases if c["category"] == only_category]
    if limit is not None:
        cases = cases[:limit]
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the golden eval against the live /agent/chat backend.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--dataset", default=str(DATASET_PATH))
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="Where to write the JSON report.",
    )
    parser.add_argument(
        "--filter",
        help="Only run cases in this category (e.g. session_search).",
    )
    parser.add_argument(
        "--ids",
        help="Comma-separated test IDs to run (e.g. TC033,TC037).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Run at most N cases (after filtering).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep between cases (use to pace Gemini RPM).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in the console output.",
    )
    parser.add_argument(
        "--opik",
        action="store_true",
        help="Log each golden case as a separate trace to Opik (needs OPIK_* in .env).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    color_enabled = sys.stdout.isatty() and not args.no_color

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}", file=sys.stderr)
        return 2
    with dataset_path.open() as f:
        dataset = json.load(f)
    cases = filter_cases(
        dataset["test_cases"],
        only_ids=args.ids.split(",") if args.ids else None,
        only_category=args.filter,
        limit=args.limit,
    )
    if not cases:
        print("No test cases matched the filters.", file=sys.stderr)
        return 2

    api = APIClient(args.base_url)
    if not api.health():
        print(
            f"Backend at {args.base_url}/health is not responding. "
            f"Start it with: `uvicorn app.main:app --reload --port 8000`",
            file=sys.stderr,
        )
        return 2

    print(f"Running {len(cases)} case(s) against {args.base_url}")
    print(f"Sleep between cases: {args.sleep}s")
    print("=" * 64)

    started = time.time()
    results: list[CaseResult] = []
    try:
        for i, case in enumerate(cases):
            result = run_case(api, case)
            results.append(result)
            print_case_line(result, color_enabled)
            if args.opik:
                log_opik_golden_case(case, result)
            if args.sleep and i < len(cases) - 1:
                time.sleep(args.sleep)
    finally:
        api.close()

    elapsed = time.time() - started
    metrics = aggregate_metrics(results)
    print_summary(results, metrics, elapsed, color_enabled)
    save_report(Path(args.report), args.base_url, results, metrics, elapsed)

    # Exit code: 0 if all passed, 1 if any failure/error.
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
