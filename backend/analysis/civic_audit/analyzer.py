"""
Civic accountability–oriented heuristics over a Python codebase.

Scores and findings are signals for review, not institutional certifications.
"""

from __future__ import annotations

import ast
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from analysis.archaeology.extractor import extract_repository


@dataclass
class CivicAuditFinding:
    """Single heuristic finding."""

    category: str
    severity: str  # critical, high, medium, low
    title: str
    description: str
    file_path: str
    line_number: int
    code_snippet: str
    recommendation: str
    attack_vector: Optional[str] = None
    confidence: str = "medium"


@dataclass
class CivicAuditResult:
    """Aggregated civic audit output."""

    repo_path: str
    findings: List[CivicAuditFinding] = field(default_factory=list)
    pattern_rules_found: List[str] = field(default_factory=list)
    signing_flows: List[Dict[str, Any]] = field(default_factory=list)
    temporal_logic: List[Dict[str, Any]] = field(default_factory=list)
    data_integrity: List[Dict[str, Any]] = field(default_factory=list)

    corruption_detection_score: float = 0.0
    temporal_integrity_score: float = 0.0
    cryptographic_robustness_score: float = 0.0
    transparency_score: float = 0.0
    overall_civic_score: float = 0.0
    duration_seconds: Optional[float] = None


class CivicAuditAnalyzer:
    """Heuristic civic/accountability-style scan (patterns, crypto keywords, temporal hints)."""

    PATTERN_RULES = [
        "SOFT_BUNDLE_V1",
        "SECTOR_CONVERGENCE_V1",
        "GEO_MISMATCH_V1",
        "REVOLVING_DOOR_V1",
        "BASELINE_ANOMALY_V1",
        "ALIGNMENT_ANOMALY_V1",
        "AMENDMENT_TELL_V1",
        "HEARING_TESTIMONY_V1",
        "COMMITTEE_SWEEP_V1",
        "FINGERPRINT_BLOOM_V1",
        "TEMPORAL_PROXIMITY_V1",
        "DONATION_CLUSTER_V1",
        "VOTE_PATTERN_V1",
        "DISCLOSURE_GAP_V1",
        "CONFLICT_SIGNAL_V1",
        "TRANSPARENCY_BREACH_V1",
        "ACCOUNTABILITY_VOID_V1",
        "ETHICS_VIOLATION_V1",
    ]

    CRYPTO_PATTERNS = [
        "Ed25519",
        "SHA-256",
        "signing",
        "verification",
        "hash",
        "signature",
        "receipt",
        "timestamp",
        "integrity",
        "tamper",
        "audit_trail",
    ]

    TEMPORAL_KEYWORDS = [
        "proximity",
        "timeline",
        "sequence",
        "before",
        "after",
        "during",
        "adjacent",
        "concurrent",
        "overlap",
        "gap",
        "interval",
    ]

    async def analyze_civic_accountability(self, repo_path: Path) -> CivicAuditResult:
        t0 = time.monotonic()
        result = CivicAuditResult(repo_path=str(repo_path.resolve()))
        _bundle = extract_repository(repo_path)
        entities = _bundle.entities

        await self._analyze_pattern_rules(repo_path, entities, result)
        await self._analyze_signing_flows(repo_path, entities, result)
        await self._analyze_temporal_logic(repo_path, entities, result)
        await self._analyze_data_integrity(repo_path, entities, result)
        await self._run_adversarial_tests(repo_path, result)
        self._calculate_civic_scores(result)

        result.findings.append(
            CivicAuditFinding(
                category="methodology",
                severity="low",
                title="Heuristic civic audit (not a formal security audit)",
                description=(
                    "Scores derive from keyword/AST heuristics and coarse file scans. "
                    "Treat as triage signals; confirm critical items manually."
                ),
                file_path="",
                line_number=0,
                code_snippet="",
                recommendation="Pair with manual review and project-specific threat modeling.",
                confidence="high",
            )
        )
        result.duration_seconds = time.monotonic() - t0
        return result

    async def _analyze_pattern_rules(self, repo_path: Path, _entities: List, result: CivicAuditResult) -> None:
        pattern_files: List[Path] = []
        for py_file in repo_path.rglob("*.py"):
            if any(k in py_file.name.lower() for k in ["pattern", "rule", "detection", "engine"]):
                pattern_files.append(py_file)

        for file_path in pattern_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        for rule in self.PATTERN_RULES:
                            if rule.lower() in node.name.lower():
                                if rule not in result.pattern_rules_found:
                                    result.pattern_rules_found.append(rule)
                                finding = self._assess_pattern_rule_robustness(rule, node, file_path, content)
                                if finding:
                                    result.findings.append(finding)

                    elif isinstance(node, ast.ClassDef):
                        if any(k in node.name.lower() for k in ["pattern", "engine", "detector"]):
                            finding = self._assess_pattern_engine_design(node, file_path, content)
                            if finding:
                                result.findings.append(finding)

            except Exception as e:  # noqa: BLE001
                result.findings.append(
                    CivicAuditFinding(
                        category="analysis_error",
                        severity="medium",
                        title="Pattern analysis failed",
                        description=f"Could not analyze {file_path.name}: {e}",
                        file_path=str(file_path),
                        line_number=1,
                        code_snippet="",
                        recommendation="Review file syntax and encoding",
                    )
                )

    def _assess_pattern_rule_robustness(
        self, rule: str, node: ast.FunctionDef, file_path: Path, content: str
    ) -> Optional[CivicAuditFinding]:
        lines = content.split("\n")
        start_line = node.lineno
        end_line = node.end_lineno or start_line + 10
        snippet = "\n".join(lines[start_line - 1 : end_line])

        if re.search(r"\d+\.\d+", snippet) or re.search(r">\s*\d+", snippet):
            return CivicAuditFinding(
                category="corruption_detection",
                severity="medium",
                title=f"Possible hardcoded threshold in {rule}",
                description=f"Rule {rule} contains numeric thresholds; review for configurability.",
                file_path=str(file_path),
                line_number=start_line,
                code_snippet=snippet[:200],
                recommendation="Consider configurable or statistically grounded thresholds.",
                attack_vector="Threshold shaping (staying below static limits) may evade detection",
            )

        if "try:" not in snippet and "except" not in snippet:
            return CivicAuditFinding(
                category="reliability",
                severity="high",
                title=f"No obvious try/except in {rule}",
                description=f"Rule {rule} body has no try/except in this slice; failures may propagate.",
                file_path=str(file_path),
                line_number=start_line,
                code_snippet=snippet[:200],
                recommendation="Add explicit error handling and logging for detection paths.",
                attack_vector="Silent failures could hide bad inputs or parser errors",
            )

        return None

    def _assess_pattern_engine_design(
        self, node: ast.ClassDef, file_path: Path, content: str
    ) -> Optional[CivicAuditFinding]:
        methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        essential = ["run", "execute", "analyze", "detect"]
        if not any(m in methods for m in essential):
            return CivicAuditFinding(
                category="architecture",
                severity="high",
                title="Missing conventional engine entrypoint name",
                description=f"Class {node.name} has no run/execute/analyze/detect method (heuristic).",
                file_path=str(file_path),
                line_number=node.lineno,
                code_snippet=f"class {node.name}:",
                recommendation="Expose a clear entry API for the engine.",
            )
        return None

    async def _analyze_signing_flows(self, repo_path: Path, _entities: List, result: CivicAuditResult) -> None:
        signing_files: List[Path] = []
        for py_file in repo_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if any(p.lower() in content.lower() for p in self.CRYPTO_PATTERNS[:6]):
                signing_files.append(py_file)

        for file_path in signing_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                if "sign(" in content or ".sign(" in content:
                    flow: Dict[str, Any] = {"file": str(file_path), "type": "signing", "algorithms": []}
                    for pattern in self.CRYPTO_PATTERNS:
                        if pattern in content:
                            flow["algorithms"].append(pattern)
                    result.signing_flows.append(flow)
                    finding = self._assess_signing_security(file_path, content)
                    if finding:
                        result.findings.append(finding)

                if "verify(" in content or ".verify(" in content:
                    finding = self._assess_verification_robustness(file_path, content)
                    if finding:
                        result.findings.append(finding)
            except OSError:
                continue

    def _assess_signing_security(self, file_path: Path, content: str) -> Optional[CivicAuditFinding]:
        if re.search(r'private_key\s*=\s*["\']', content):
            return CivicAuditFinding(
                category="cryptographic_security",
                severity="critical",
                title="Possible hardcoded private key material",
                description="Literal assignment to private_key detected (heuristic).",
                file_path=str(file_path),
                line_number=1,
                code_snippet="private_key = …",
                recommendation="Use secret management; never commit key material.",
                attack_vector="Key exposure via repository",
                confidence="medium",
            )

        if "random.random()" in content or ("time.time()" in content and "secret" not in content.lower()):
            return CivicAuditFinding(
                category="cryptographic_security",
                severity="high",
                title="Possible weak randomness",
                description="Uses random.random() or time.time(); verify crypto use cases.",
                file_path=str(file_path),
                line_number=1,
                code_snippet="",
                recommendation="Use secrets module or os.urandom for cryptographic randomness.",
                attack_vector="Predictability if used for security-sensitive nonces",
            )

        return None

    def _assess_verification_robustness(self, file_path: Path, content: str) -> Optional[CivicAuditFinding]:
        verify_lines = [line for line in content.split("\n") if "verify(" in line]
        for line in verify_lines:
            if "try:" not in content or "except" not in content:
                idx = content.split("\n").index(line) + 1
                return CivicAuditFinding(
                    category="verification_robustness",
                    severity="high",
                    title="Verification present; file lacks try/except (coarse check)",
                    description="Whole-file scan: no try/except near verification paths (heuristic).",
                    file_path=str(file_path),
                    line_number=idx,
                    code_snippet=line[:200],
                    recommendation="Ensure verification errors are handled explicitly.",
                    attack_vector="Unhandled verification errors may be ambiguous to callers",
                )
        return None

    async def _analyze_temporal_logic(self, repo_path: Path, _entities: List, result: CivicAuditResult) -> None:
        for py_file in repo_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                indicators = sum(1 for kw in self.TEMPORAL_KEYWORDS if kw.lower() in content.lower())
                if indicators >= 3:
                    result.temporal_logic.append({"file": str(py_file), "indicators": indicators})
                    finding = self._assess_temporal_robustness(py_file, content)
                    if finding:
                        result.findings.append(finding)
            except OSError:
                continue

    def _assess_temporal_robustness(self, file_path: Path, content: str) -> Optional[CivicAuditFinding]:
        if "datetime" in content and "timezone" not in content and "UTC" not in content:
            return CivicAuditFinding(
                category="temporal_integrity",
                severity="medium",
                title="datetime without explicit timezone/UTC (heuristic)",
                description="Mixed naive timestamps can cause boundary bugs in timelines.",
                file_path=str(file_path),
                line_number=1,
                code_snippet="",
                recommendation="Prefer UTC-aware datetimes for audit timelines.",
                attack_vector="Ambiguous local time in cross-region analysis",
            )
        return None

    async def _analyze_data_integrity(self, repo_path: Path, _entities: List, result: CivicAuditResult) -> None:
        for py_file in repo_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if any(p in content for p in ["hash", "checksum", "integrity", "tamper"]):
                    result.data_integrity.append(
                        {
                            "file": str(py_file),
                            "mechanisms": [p for p in ["hash", "checksum", "integrity", "tamper"] if p in content],
                        }
                    )
                    finding = self._assess_integrity_implementation(py_file, content)
                    if finding:
                        result.findings.append(finding)
            except OSError:
                continue

    def _assess_integrity_implementation(self, file_path: Path, content: str) -> Optional[CivicAuditFinding]:
        if "hash" in content and "verify" not in content and "check" not in content:
            return CivicAuditFinding(
                category="data_integrity",
                severity="medium",
                title="Hash mention without verify/check (heuristic)",
                description="May still verify elsewhere; confirm domain semantics.",
                file_path=str(file_path),
                line_number=1,
                code_snippet="",
                recommendation="Ensure integrity checks cover tamper detection where required.",
            )
        return None

    async def _run_adversarial_tests(self, repo_path: Path, result: CivicAuditResult) -> None:
        scenarios = [
            "threshold_gaming",
            "timing_attacks",
            "data_pollution",
            "signature_replay",
            "denial_of_service",
        ]
        for scenario in scenarios:
            finding = self._simulate_attack_scenario(scenario, result)
            if finding:
                result.findings.append(finding)

    def _simulate_attack_scenario(self, scenario: str, result: CivicAuditResult) -> Optional[CivicAuditFinding]:
        if scenario == "threshold_gaming" and result.pattern_rules_found:
            return CivicAuditFinding(
                category="adversarial_robustness",
                severity="high",
                title="Threshold gaming (conceptual)",
                description="If rules use static thresholds, adversaries may optimize below limits.",
                file_path="(methodology)",
                line_number=0,
                code_snippet="",
                recommendation="Review adaptive thresholds, auditing, and peer checks.",
                attack_vector="Activity shaped under detection limits",
            )
        return None

    def _calculate_civic_scores(self, result: CivicAuditResult) -> None:
        critical = sum(1 for f in result.findings if f.severity == "critical")
        high = sum(1 for f in result.findings if f.severity == "high")

        pattern_coverage = min(1.0, len(set(result.pattern_rules_found)) / max(len(self.PATTERN_RULES), 1))
        corruption_penalties = critical * 0.3 + high * 0.1
        result.corruption_detection_score = max(0.0, min(1.0, pattern_coverage - corruption_penalties))

        temporal_coverage = min(1.0, len(result.temporal_logic) / 5.0)
        temporal_penalties = sum(1 for f in result.findings if f.category == "temporal_integrity") * 0.2
        result.temporal_integrity_score = max(0.0, min(1.0, temporal_coverage - temporal_penalties))

        crypto_coverage = min(1.0, len(result.signing_flows) / 3.0)
        crypto_penalties = sum(1 for f in result.findings if f.category == "cryptographic_security") * 0.4
        result.cryptographic_robustness_score = max(0.0, min(1.0, crypto_coverage - crypto_penalties))

        transparency_penalties = sum(1 for f in result.findings if f.category == "reliability") * 0.15
        result.transparency_score = max(0.0, min(1.0, 1.0 - transparency_penalties))

        scores = [
            result.corruption_detection_score,
            result.temporal_integrity_score,
            result.cryptographic_robustness_score,
            result.transparency_score,
        ]
        result.overall_civic_score = sum(scores) / len(scores)
