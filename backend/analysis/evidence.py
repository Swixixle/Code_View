"""
Code View - Analysis engine: Python AST parsing, claims, mechanisms, contradictions.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from models.evidence import (
    AnalysisEvidence,
    ClaimEvidence,
    Contradiction,
    EvidenceItem,
    EvidenceStatus,
    EvidenceType,
    ConfidenceLevel,
    ExtractedSymbol,
    MechanismTrace,
)
from analysis.claims_enhanced import extract_enhanced_claims
from analysis.parsers.python_parser_enhanced import parse_python_directory_enhanced

logger = logging.getLogger(__name__)

# Stages produced by `claims_enhanced` — used to split doc-claim evidence after refinement
CLAIM_EVIDENCE_STAGES = frozenset(
    {
        "enhanced_claims_extraction",
        "cryptographic_claims_extraction",
        "evidence_claims_extraction",
        "credibility_claims_extraction",
        "feature_claims_extraction",
    }
)


class AnalysisEngine:
    """Coordinates parsing, documentation claims, and contradiction detection."""

    def __init__(self) -> None:
        self.supported_languages = ["python", "javascript", "typescript"]

    async def analyze_codebase(self, repo_path: Path, repo_url: str) -> AnalysisEvidence:
        analysis_started = datetime.now()
        analysis_id = f"analysis_{int(analysis_started.timestamp())}"

        analysis = AnalysisEvidence(
            analysis_id=analysis_id,
            repository_url=repo_url,
            commit_hash="unknown",
            branch="unknown",
            analysis_started=analysis_started,
        )

        try:
            commit_hash, branch = await self._get_repo_metadata(repo_path)
            analysis.commit_hash = commit_hash
            analysis.branch = branch

            logger.info("Starting analysis %s for %s", analysis_id, repo_url)

            analysis.stages_completed.append("file_classification")
            language_stats = self._classify_files(repo_path)

            if language_stats.get("python", 0) > 0:
                logger.info("Analyzing Python files (crypto-aware enhanced parser)...")
                python_evidence = parse_python_directory_enhanced(repo_path)
                analysis.all_evidence.extend(python_evidence)
                analysis.stages_completed.append("python_parsing")

            logger.info("Extracting claims from documentation...")
            claims_evidence = await self._extract_claims(repo_path)
            analysis.all_evidence.extend(claims_evidence)
            analysis.stages_completed.append("claims_extraction")

            from analysis.refinement import apply_analysis_refinement

            apply_analysis_refinement(analysis)
            analysis.stages_completed.append("evidence_refinement")

            claims_evidence = [e for e in analysis.all_evidence if e.analysis_stage in CLAIM_EVIDENCE_STAGES]

            logger.info("Mapping claims to mechanisms...")
            analysis.mechanisms = self._map_mechanisms(analysis.all_evidence)
            analysis.stages_completed.append("mechanism_mapping")

            logger.info("Detecting contradictions...")
            contradictions = self._detect_contradictions(analysis.all_evidence, claims_evidence)
            analysis.contradictions = contradictions
            analysis.stages_completed.append("contradiction_detection")

            analysis.claims = self._assemble_claims(
                analysis.all_evidence, claims_evidence, contradictions
            )
            analysis.stages_completed.append("claims_assembly")

            analysis.analysis_completed = datetime.now()
            analysis.analysis_duration = (analysis.analysis_completed - analysis_started).total_seconds()
            analysis.coverage_percentage = self._calculate_coverage(analysis)

            logger.info("Analysis %s completed in %.2fs", analysis_id, analysis.analysis_duration or 0)
            return analysis

        except Exception as e:  # noqa: BLE001
            logger.error("Analysis %s failed: %s", analysis_id, e)
            analysis.stages_failed.append(str(e))
            analysis.analysis_completed = datetime.now()
            analysis.analysis_duration = (analysis.analysis_completed - analysis_started).total_seconds()
            return analysis

    async def _get_repo_metadata(self, repo_path: Path) -> Tuple[str, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "rev-parse",
                "HEAD",
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            commit_hash = stdout.decode().strip() if proc.returncode == 0 else "unknown"

            proc = await asyncio.create_subprocess_exec(
                "git",
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            branch = stdout.decode().strip() if proc.returncode == 0 else "unknown"

            return commit_hash or "unknown", branch or "unknown"
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not get repository metadata: %s", e)
            return "unknown", "unknown"

    def _classify_files(self, repo_path: Path) -> Dict[str, int]:
        language_stats: Dict[str, int] = {}
        extensions = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
        }

        for file_path in repo_path.rglob("*"):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                if suffix in extensions:
                    language = extensions[suffix]
                    language_stats[language] = language_stats.get(language, 0) + 1

        return language_stats

    async def _extract_claims(self, repo_path: Path) -> List[EvidenceItem]:
        return extract_enhanced_claims(repo_path)

    def _map_mechanisms(self, evidence: List[EvidenceItem]) -> List[MechanismTrace]:
        mechanisms: List[MechanismTrace] = []

        routes = [
            e
            for e in evidence
            if any("route" in s.type for s in e.extracted_symbols)
        ]
        functions = [
            e
            for e in evidence
            if any("function" in s.type for s in e.extracted_symbols)
        ]

        if routes:
            entry_points = [s for e in routes for s in e.extracted_symbols]
            mechanisms.append(
                MechanismTrace(
                    claim_id="rest_api",
                    implementation_path=["route_handlers"],
                    entry_points=entry_points,
                    data_flow=[],
                    dependencies=[],
                )
            )

        core_functions = [
            e
            for e in functions
            if any(
                keyword in e.claim.lower()
                for keyword in ["investigate", "analyze", "pattern", "detect", "sign", "verify"]
            )
        ]
        if core_functions:
            entry_points = [s for e in core_functions for s in e.extracted_symbols]
            mechanisms.append(
                MechanismTrace(
                    claim_id="core_logic",
                    implementation_path=["functions"],
                    entry_points=entry_points,
                    data_flow=[],
                    dependencies=[],
                )
            )

        crypto_evidence = [
            e
            for e in evidence
            if any(
                "crypto" in s.type or "sign" in s.type or "hash" in s.type for s in e.extracted_symbols
            )
            or "cryptographic" in e.claim.lower()
            or "signature" in e.claim.lower()
        ]
        if crypto_evidence:
            entry_points = [s for e in crypto_evidence for s in e.extracted_symbols]
            mechanisms.append(
                MechanismTrace(
                    claim_id="cryptography_and_security",
                    implementation_path=["crypto_signing", "verification", "hashing"],
                    entry_points=entry_points[:50],
                    data_flow=[],
                    dependencies=[],
                )
            )

        return mechanisms

    def _detect_contradictions(
        self, code_evidence: List[EvidenceItem], claims_evidence: List[EvidenceItem]
    ) -> List[Contradiction]:
        contradictions: List[Contradiction] = []
        max_items = 40

        implemented_functions: List[str] = []
        for evidence in code_evidence:
            for symbol in evidence.extracted_symbols:
                implemented_functions.append(symbol.name.lower())

        for claim_evidence in claims_evidence:
            if len(contradictions) >= max_items:
                break
            claim_text = claim_evidence.claim.lower()
            has_implementation = False
            for func_name in implemented_functions:
                claim_keywords = [w for w in claim_text.split() if len(w) > 3]
                if any(keyword in func_name for keyword in claim_keywords):
                    has_implementation = True
                    break

            if not has_implementation:
                contradictions.append(
                    Contradiction(
                        title="Unimplemented documentation claim",
                        description=(
                            f"Documentation suggests '{claim_evidence.claim}' but no "
                            "clear matching symbol names were found."
                        ),
                        severity="medium",
                        claimed_behavior=claim_evidence.claim,
                        actual_behavior="No matching functions or classes detected by name overlap",
                        evidence_for_claim=[claim_evidence.id],
                        evidence_against_claim=[],
                    )
                )

        return contradictions

    def _assemble_claims(
        self,
        code_evidence: List[EvidenceItem],
        claims_evidence: List[EvidenceItem],
        contradictions: List[Contradiction],
    ) -> List[ClaimEvidence]:
        assembled: List[ClaimEvidence] = []
        contradiction_titles = {c.claimed_behavior.lower() for c in contradictions}

        for claim_item in claims_evidence:
            supporting_evidence: List[EvidenceItem] = []
            contradicting_evidence: List[EvidenceItem] = []

            claim_keywords = [w for w in claim_item.claim.lower().split() if len(w) > 3]
            for code_item in code_evidence:
                code_text = code_item.claim.lower()
                if any(kw in code_text for kw in claim_keywords):
                    supporting_evidence.append(code_item)

            if claim_item.claim.lower() in contradiction_titles or any(
                claim_item.claim.lower() in c.description.lower() for c in contradictions
            ):
                contradicting_evidence.append(
                    EvidenceItem(
                        claim=f"Possible gap: {claim_item.claim}",
                        status=EvidenceStatus.CONTRADICTED,
                        evidence_type=EvidenceType.INFERRED,
                        confidence=ConfidenceLevel.MEDIUM,
                        source_locations=[],
                        reasoning_chain=["Heuristic: doc claim without strong code name match"],
                        analysis_stage="contradiction_detection",
                    )
                )

            if contradicting_evidence:
                status = EvidenceStatus.CONTRADICTED
                confidence = 0.2
            elif supporting_evidence:
                status = EvidenceStatus.SUPPORTED
                confidence = 0.8
            else:
                status = EvidenceStatus.UNKNOWN
                confidence = 0.5

            assembled.append(
                ClaimEvidence(
                    claim_text=claim_item.claim,
                    category="capability",
                    supporting_evidence=supporting_evidence,
                    contradicting_evidence=contradicting_evidence,
                    overall_status=status,
                    confidence_score=confidence,
                )
            )

        assembled.extend(self._generate_implementation_claims(code_evidence))
        return assembled

    def _generate_implementation_claims(self, code_evidence: List[EvidenceItem]) -> List[ClaimEvidence]:
        implementation_claims: List[ClaimEvidence] = []

        route_evidence = [e for e in code_evidence if "endpoint" in e.claim.lower()]
        function_evidence = [e for e in code_evidence if "function" in e.claim.lower()]
        class_evidence = [e for e in code_evidence if "class" in e.claim.lower()]

        if route_evidence:
            implementation_claims.append(
                ClaimEvidence(
                    claim_text=f"REST API with {len(route_evidence)} route-related evidence items",
                    category="implementation",
                    supporting_evidence=route_evidence,
                    contradicting_evidence=[],
                    overall_status=EvidenceStatus.SUPPORTED,
                    confidence_score=0.9,
                )
            )

        if function_evidence:
            implementation_claims.append(
                ClaimEvidence(
                    claim_text=f"Python implementation with {len(function_evidence)} function-related evidence items",
                    category="implementation",
                    supporting_evidence=function_evidence,
                    contradicting_evidence=[],
                    overall_status=EvidenceStatus.SUPPORTED,
                    confidence_score=0.9,
                )
            )

        if class_evidence:
            implementation_claims.append(
                ClaimEvidence(
                    claim_text=f"Class definitions observed ({len(class_evidence)} evidence items)",
                    category="implementation",
                    supporting_evidence=class_evidence,
                    contradicting_evidence=[],
                    overall_status=EvidenceStatus.SUPPORTED,
                    confidence_score=0.85,
                )
            )

        return implementation_claims

    def _calculate_coverage(self, analysis: AnalysisEvidence) -> float:
        total_stages = 7
        return (len(analysis.stages_completed) / total_stages) * 100.0
