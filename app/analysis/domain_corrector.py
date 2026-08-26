from dataclasses import dataclass
from collections.abc import Iterable
import json
from pathlib import Path


@dataclass(frozen=True)
class DomainCorrectionRule:
    rule_id: str
    source: str
    target: str
    reason: str
    kind: str = "typo"
    context_terms: tuple[str, ...] = ()
    context_window: int = 20


@dataclass(frozen=True)
class AppliedCorrection:
    rule_id: str
    source: str
    target: str
    reason: str
    kind: str = "typo"


@dataclass(frozen=True)
class DomainCorrectionResult:
    raw_transcript: str
    corrected_transcript: str
    corrections: tuple[AppliedCorrection, ...]


class DomainTermCorrector:
    """Apply a reviewed, ordered allowlist of domain phrase corrections."""

    def __init__(
        self,
        rules: Iterable[DomainCorrectionRule],
        enabled_kinds: Iterable[str] = ("typo",),
    ):
        self.rules = tuple(rules)
        self.enabled_kinds = frozenset(enabled_kinds)
        if not self.enabled_kinds:
            raise ValueError("at least one correction kind must be enabled")
        self._validate_rules()

    def correct(self, transcript: str) -> DomainCorrectionResult:
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")

        corrected = transcript
        applied: list[AppliedCorrection] = []
        for rule in self.rules:
            if rule.kind not in self.enabled_kinds:
                continue
            updated = self._apply_rule(corrected, rule)
            if updated != corrected:
                applied.append(
                    AppliedCorrection(
                        rule_id=rule.rule_id,
                        source=rule.source,
                        target=rule.target,
                        reason=rule.reason,
                        kind=rule.kind,
                    )
                )
                corrected = updated

        return DomainCorrectionResult(
            raw_transcript=transcript,
            corrected_transcript=corrected,
            corrections=tuple(applied),
        )

    @staticmethod
    def _apply_rule(transcript: str, rule: DomainCorrectionRule) -> str:
        if not rule.context_terms:
            return transcript.replace(rule.source, rule.target)

        parts: list[str] = []
        cursor = 0
        while True:
            index = transcript.find(rule.source, cursor)
            if index < 0:
                parts.append(transcript[cursor:])
                break
            parts.append(transcript[cursor:index])
            end = index + len(rule.source)
            context_start = max(0, index - rule.context_window)
            context_end = min(len(transcript), end + rule.context_window)
            context = transcript[context_start:context_end]
            if any(term in context for term in rule.context_terms):
                parts.append(rule.target)
            else:
                parts.append(rule.source)
            cursor = end
        return "".join(parts)

    def _validate_rules(self) -> None:
        rule_ids: set[str] = set()
        sources: set[str] = set()
        for rule in self.rules:
            if (
                not rule.rule_id.strip()
                or not rule.source.strip()
                or not rule.reason.strip()
            ):
                raise ValueError("correction rule fields must not be empty")
            if rule.kind not in {"typo", "spacing"}:
                raise ValueError("unsupported correction kind")
            if any(not term.strip() for term in rule.context_terms):
                raise ValueError("context terms must not be empty")
            if rule.context_terms and rule.context_window <= 0:
                raise ValueError("context window must be positive")
            if rule.source == rule.target:
                raise ValueError("correction rule source and target must differ")
            if rule.rule_id in rule_ids:
                raise ValueError(f"duplicate correction rule id: {rule.rule_id}")
            if rule.source in sources:
                raise ValueError(f"duplicate correction source: {rule.source}")
            rule_ids.add(rule.rule_id)
            sources.add(rule.source)


def load_default_domain_rules(
    path: str | Path | None = None,
) -> tuple[DomainCorrectionRule, ...]:
    rules_path = Path(path) if path is not None else Path("data/stt_dictionary/domain_corrections.json")
    try:
        entries = json.loads(rules_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"failed to load domain correction rules: {rules_path}") from exc
    if not isinstance(entries, list):
        raise ValueError("domain correction rules must be a list")
    try:
        rules = tuple(DomainCorrectionRule(**entry) for entry in entries)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid domain correction rule entry") from exc
    DomainTermCorrector(rules)
    return rules
