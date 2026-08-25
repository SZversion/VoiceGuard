import argparse
import json
import os
import time
from pathlib import Path

import httpx

from tools.model_evaluation import EvaluationCase, compute_metrics


def parse_case(value: str) -> tuple[Path, str]:
    try:
        path_text, expected_label = value.rsplit("=", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "case must use FILE_PATH=normal or FILE_PATH=voice_phishing"
        ) from exc
    path = Path(path_text)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"audio file does not exist: {path}")
    if expected_label not in {"normal", "voice_phishing"}:
        raise argparse.ArgumentTypeError(f"unsupported expected label: {expected_label}")
    return path, expected_label


def evaluate_case(
    client: httpx.Client,
    api_base: str,
    path: Path,
    expected_label: str,
    poll_seconds: float,
    timeout_seconds: float,
) -> tuple[EvaluationCase, dict[str, object]]:
    with path.open("rb") as audio_file:
        response = client.post(
            f"{api_base}/api/analyze",
            files={"audio": (path.name, audio_file, "audio/wav")},
        )
    response.raise_for_status()
    job_id = response.json()["job_id"]
    deadline = time.monotonic() + timeout_seconds

    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"evaluation timed out: {path}")
        time.sleep(poll_seconds)
        status_response = client.get(f"{api_base}/api/analyze/{job_id}/status")
        status_response.raise_for_status()
        status = status_response.json()
        print(json.dumps({"file": str(path), **status}, ensure_ascii=False))
        if status["status"] == "failed":
            raise RuntimeError(f"analysis failed for {path}: {status}")
        if status["status"] == "completed":
            break

    result_response = client.get(f"{api_base}/api/analyze/{job_id}/result")
    result_response.raise_for_status()
    result_payload = result_response.json()
    result = result_payload["result"]
    case = EvaluationCase(
        expected_label=expected_label,
        predicted_label=result["label"],
        suspicion_score=float(result["suspicion_score"]),
    )
    return case, {
        "file": str(path),
        "job_id": job_id,
        "expected_label": expected_label,
        "predicted_label": case.predicted_label,
        "suspicion_score": case.suspicion_score,
        "reference_segments": result.get("reference_segments", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the deployed analysis API with explicitly supplied labels."
    )
    parser.add_argument(
        "--api",
        default=os.getenv("API_BASE_URL"),
        required=os.getenv("API_BASE_URL") is None,
    )
    parser.add_argument("--case", action="append", type=parse_case, required=True)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    args = parser.parse_args()

    api_base = args.api.rstrip("/")
    cases = []
    details = []
    with httpx.Client(timeout=30.0) as client:
        for path, expected_label in args.case:
            case, detail = evaluate_case(
                client,
                api_base,
                path,
                expected_label,
                args.poll_seconds,
                args.timeout_seconds,
            )
            cases.append(case)
            details.append(detail)

    print(json.dumps({"cases": details, "metrics": compute_metrics(cases)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())