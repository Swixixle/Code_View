"""
Code View - Educational Dossier Generator
Comprehensive forensic analysis reports with educational value
"""

from typing import List

from models.evidence import AnalysisEvidence, EvidenceItem

class EducationalDossierGenerator:
    """Generates comprehensive educational forensic dossiers"""
    
    def __init__(self):
        self.educational_frameworks = {
            'civic_technology': {
                'patterns': ['investigation', 'pattern', 'corruption', 'transparency', 'accountability'],
                'concepts': ['Evidence-first design', 'Procedural trust', 'Institutional credibility', 'Cryptographic verification']
            },
            'cryptographic_systems': {
                'patterns': ['ed25519', 'signing', 'verification', 'hash', 'receipt', 'proof'],
                'concepts': ['Digital signatures', 'Hash functions', 'Trust boundaries', 'Cryptographic receipts']
            },
            'software_architecture': {
                'patterns': ['api', 'database', 'class', 'function', 'route', 'endpoint'],
                'concepts': ['Layered architecture', 'Separation of concerns', 'API design', 'Data modeling']
            }
        }
    
    def generate_comprehensive_dossier(self, analysis: AnalysisEvidence, include_educational: bool = True) -> str:
        """Generate complete educational forensic dossier"""
        
        dossier_sections = []
        
        # Title and metadata
        dossier_sections.append(self._generate_title_section(analysis))
        
        # Executive summary with educational context
        dossier_sections.append(self._generate_executive_summary(analysis, include_educational))
        
        # Forensic methodology explanation
        if include_educational:
            dossier_sections.append(self._generate_methodology_section(analysis))
        
        # Evidence analysis with educational insights
        dossier_sections.append(self._generate_evidence_analysis(analysis, include_educational))
        
        # Cryptographic verification section
        dossier_sections.append(self._generate_cryptographic_analysis(analysis))
        
        # Claims vs implementation deep dive
        dossier_sections.append(self._generate_claims_deep_dive(analysis))
        
        # Architectural patterns education
        if include_educational:
            dossier_sections.append(self._generate_architecture_education(analysis))
        
        # Institutional credibility assessment
        dossier_sections.append(self._generate_credibility_assessment(analysis))
        
        # Recommendations and next steps
        dossier_sections.append(self._generate_recommendations(analysis))
        
        # Technical appendix
        dossier_sections.append(self._generate_technical_appendix(analysis))
        
        return "\n\n".join(dossier_sections)
    
    def _generate_title_section(self, analysis: AnalysisEvidence) -> str:
        """Generate dossier title and metadata"""
        
        repo_name = self._extract_repo_name(analysis.repository_url)
        title = repo_name.replace('-', ' ').replace('_', ' ').title()
        
        return f"""# {title}: Comprehensive Forensic Code Dossier

## Document Classification
**Classification:** Educational Forensic Analysis  
**Subject:** {analysis.repository_url}  
**Analysis ID:** {analysis.analysis_id}  
**Commit Analyzed:** {analysis.commit_hash}  
**Branch:** {analysis.branch}  
**Analysis Date:** {analysis.analysis_started.strftime("%Y-%m-%d %H:%M UTC")}  
**Duration:** {f"{analysis.analysis_duration:.1f} seconds" if analysis.analysis_duration is not None else "n/a"}  
**Completeness:** {analysis.coverage_percentage:.1f}%  

## Purpose Statement

This dossier provides evidence-backed forensic analysis of the software system, examining the gap between documented capabilities and actual implementation. All findings include source code references and confidence assessments suitable for institutional review.

**Methodology:** Evidence extraction via Python AST parsing, claims analysis from documentation, and cryptographic verification pattern detection.

---"""
    
    def _generate_executive_summary(self, analysis: AnalysisEvidence, include_educational: bool) -> str:
        """Generate executive summary with educational context"""
        
        sections = ["## Executive Summary\n"]
        
        # Core findings
        evidence_count = len(analysis.all_evidence)
        crypto_evidence = self._count_crypto_evidence(analysis.all_evidence)
        high_confidence_evidence = len([e for e in analysis.all_evidence if e.confidence.value == "high"])
        
        sections.append("### Key Findings")
        sections.append(f"- **{evidence_count} evidence items** extracted from source code with exact locations")
        sections.append(f"- **{len(analysis.claims)} documented claims** analyzed for implementation alignment")
        sections.append(f"- **{len(analysis.contradictions)} potential contradictions** between documentation and code")
        sections.append(f"- **{crypto_evidence} cryptographic components** detected (signing, verification, hashing)")
        pct_hi = (high_confidence_evidence / evidence_count * 100) if evidence_count else 0.0
        sections.append(f"- **{high_confidence_evidence} high-confidence findings** ({pct_hi:.0f}% of total)")

        if getattr(analysis, "refinement_metadata", None):
            sections.append(self._refinement_executive_snippet(analysis))
        
        # System classification
        framework = self._classify_system_type(analysis.all_evidence)
        sections.append(f"\n### System Classification")
        sections.append(f"**Primary Framework:** {framework}")
        
        if include_educational:
            sections.append(f"**Educational Value:** This system demonstrates {self._get_educational_patterns(analysis)}")
        
        # Trust assessment
        trust_score = self._calculate_trust_score(analysis)
        sections.append(f"\n### Institutional Trust Assessment")
        sections.append(f"**Trust Score:** {trust_score}/100")
        sections.append(self._get_trust_explanation(trust_score, analysis))
        
        return "\n".join(sections)
    
    def _refinement_executive_snippet(self, analysis: AnalysisEvidence) -> str:
        """Summarize deduplication + classification when `refinement_metadata` is present."""
        meta = analysis.refinement_metadata or {}
        dedup = meta.get("deduplication") or {}
        cls = meta.get("classification") or {}
        tone = meta.get("tone_calibration") or {}
        lines = ["\n### Evidence refinement (deduplication and labeling)\n"]
        if dedup:
            lines.append(
                f"- **Post-deduplication count:** {dedup.get('deduplicated_count', '?')} items "
                f"(from {dedup.get('original_count', '?')}; ~{dedup.get('reduction_percentage', 0):.0f}% reduction)."
            )
        impl = cls.get("implementation_combined") or {}
        if impl:
            lines.append(
                f"- **Implementation-like share:** ~{impl.get('percentage', 0):.0f}% of items "
                "(`verified_implementation` + `likely_implementation`)."
            )
        pat = cls.get("detected_patterns") or {}
        if pat:
            lines.append(
                f"- **Pattern-heavy items:** ~{pat.get('percentage', 0):.0f}% flagged as `detected_pattern`."
            )
        qs = tone.get("quality_summary") or {}
        if qs:
            eq = str(qs.get("evidence_quality", "")).replace("_", " ")
            at = str(qs.get("analysis_type", "")).replace("_", " ")
            lines.append(f"- **Calibrated quality stance:** {eq} ({at}).")
        headline = meta.get("quality_headline")
        if headline:
            lines.append(f"- **Summary:** {headline}")
        lines.append("")
        lines.append(
            "Headline counts above are **after deduplication**; interpret contradictory or "
            "high-stakes claims using source locations and per-item `refinement_signal`."
        )
        return "\n".join(lines)
    
    def _generate_methodology_section(self, analysis: AnalysisEvidence) -> str:
        """Generate educational methodology section"""
        
        return """## Forensic Analysis Methodology

### Evidence Extraction Process

This analysis follows a multi-stage forensic examination designed to reveal the actual implementation versus documented claims:

1. **Static Code Analysis**: Python Abstract Syntax Tree (AST) parsing extracts functions, classes, routes, and imports with exact source locations.

2. **Cryptographic Pattern Detection**: Specialized analysis identifies Ed25519 signing, SHA-256 hashing, verification functions, and security boundaries.

3. **Claims Extraction**: Natural language processing of documentation (README, CONTRIBUTING, SECURITY files) to identify capability statements.

4. **Contradiction Analysis**: Heuristic matching between documented claims and detected implementation patterns.

5. **Trust Boundary Mapping**: Identification of verification checkpoints, signed data structures, and assumption boundaries.

### Evidence Classification System

**Evidence Types:**
- **Extracted**: Directly found in source code with high confidence
- **Inferred**: Logical deduction from code patterns  
- **Heuristic**: Pattern matching with moderate confidence
- **Not Verified**: Present but requires manual confirmation

**Confidence Levels:**
- **High**: Direct source code extraction (>90% confidence)
- **Medium**: Strong pattern matching (60-90% confidence)
- **Low**: Weak signals requiring verification (<60% confidence)

### Limitations

This is **heuristic analysis** designed to surface signals for human review, not definitive security audit. Cryptographic detection uses name/pattern matching - actual cryptographic correctness requires expert review."""
    
    def _generate_evidence_analysis(self, analysis: AnalysisEvidence, include_educational: bool) -> str:
        """Generate detailed evidence analysis section"""
        
        sections = ["## Evidence Analysis\n"]
        
        # Evidence distribution by stage
        evidence_by_stage = {}
        for evidence in analysis.all_evidence:
            stage = evidence.analysis_stage
            if stage not in evidence_by_stage:
                evidence_by_stage[stage] = []
            evidence_by_stage[stage].append(evidence)
        
        sections.append("### Evidence Distribution by Analysis Stage")
        for stage, items in evidence_by_stage.items():
            sections.append(f"- **{stage}**: {len(items)} items")
        
        # High-value evidence
        sections.append("\n### High-Value Evidence Items")
        
        high_value_evidence = [e for e in analysis.all_evidence 
                             if e.confidence.value == "high" and 
                             any(keyword in e.claim.lower() for keyword in 
                                 ['crypto', 'sign', 'verify', 'hash', 'ed25519', 'pattern', 'investigation'])]
        
        for evidence in high_value_evidence[:10]:  # Top 10
            sections.append(f"\n**Evidence ID**: `{evidence.id}`")
            sections.append(f"**Claim**: {evidence.claim}")
            sections.append(f"**Confidence**: {evidence.confidence.value}")
            sections.append(f"**Type**: {evidence.evidence_type.value}")
            
            if evidence.source_locations:
                loc = evidence.source_locations[0]
                sections.append(f"**Source**: `{loc.file_path}:{loc.line_start}`")
            
            if evidence.reasoning_chain:
                sections.append(f"**Analysis**: {evidence.reasoning_chain[0]}")
            
            if include_educational and evidence.boundary_note:
                sections.append(f"**Educational Note**: {evidence.boundary_note}")
        
        return "\n".join(sections)
    
    def _generate_cryptographic_analysis(self, analysis: AnalysisEvidence) -> str:
        """Generate cryptographic verification analysis"""
        
        sections = ["## Cryptographic Verification Analysis\n"]
        
        crypto_evidence = [e for e in analysis.all_evidence 
                          if any(crypto_word in e.claim.lower() 
                                for crypto_word in ['crypto', 'sign', 'verify', 'hash', 'ed25519', 'sha256', 'receipt', 'proof'])]
        
        if not crypto_evidence:
            sections.append("**No cryptographic implementations detected.**")
            sections.append("\nThis system does not appear to implement cryptographic verification mechanisms.")
            return "\n".join(sections)
        
        sections.append(f"**{len(crypto_evidence)} cryptographic components detected.**\n")
        
        # Categorize crypto evidence
        signing_evidence = [e for e in crypto_evidence if 'sign' in e.claim.lower()]
        verification_evidence = [e for e in crypto_evidence if 'verify' in e.claim.lower()]
        hashing_evidence = [e for e in crypto_evidence if any(h in e.claim.lower() for h in ['hash', 'sha256', 'blake2'])]
        receipt_evidence = [e for e in crypto_evidence if any(r in e.claim.lower() for r in ['receipt', 'proof', 'attestation'])]
        
        if signing_evidence:
            sections.append("### Digital Signature Implementation")
            sections.append(f"**Components**: {len(signing_evidence)} signing-related functions detected")
            
            ed25519_evidence = [e for e in signing_evidence if 'ed25519' in e.claim.lower()]
            if ed25519_evidence:
                sections.append("**Algorithm**: Ed25519 elliptic curve signatures detected")
                sections.append("**Security Properties**: Provides authenticity and non-repudiation")
                
                for evidence in ed25519_evidence[:3]:
                    if evidence.source_locations:
                        loc = evidence.source_locations[0]
                        sections.append(f"- `{loc.file_path}:{loc.line_start}` - {evidence.claim}")
        
        if verification_evidence:
            sections.append("\n### Verification Infrastructure")
            sections.append(f"**Components**: {len(verification_evidence)} verification functions")
            sections.append("**Purpose**: Enables third-party validation of signed content")
        
        if hashing_evidence:
            sections.append("\n### Cryptographic Hashing")
            sections.append(f"**Components**: {len(hashing_evidence)} hash operations")
            sections.append("**Purpose**: Ensures data integrity and enables signature verification")
        
        if receipt_evidence:
            sections.append("\n### Evidence Receipt System")
            sections.append(f"**Components**: {len(receipt_evidence)} receipt/proof mechanisms")
            sections.append("**Purpose**: Provides cryptographic proof of analysis results")
            sections.append("**Institutional Value**: Enables external verification and audit")
        
        # Trust boundary analysis
        sections.append("\n### Trust Boundary Assessment")
        
        if len(crypto_evidence) >= 10:
            sections.append("**Assessment**: Comprehensive cryptographic implementation")
            sections.append("**Trust Model**: Evidence-first with cryptographic verification")
            sections.append("**Institutional Suitability**: High - suitable for adversarial environments")
        elif len(crypto_evidence) >= 5:
            sections.append("**Assessment**: Moderate cryptographic implementation")
            sections.append("**Trust Model**: Partial verification with some trusted components")
            sections.append("**Institutional Suitability**: Medium - requires additional verification")
        else:
            sections.append("**Assessment**: Limited cryptographic implementation")
            sections.append("**Trust Model**: Primarily trust-based with minimal verification")
            sections.append("**Institutional Suitability**: Low - not suitable for adversarial review")
        
        return "\n".join(sections)
    
    def _generate_claims_deep_dive(self, analysis: AnalysisEvidence) -> str:
        """Generate detailed claims vs implementation analysis"""
        
        sections = ["## Claims vs Implementation Deep Dive\n"]
        
        if not analysis.claims:
            sections.append("**No documented claims detected in repository.**")
            return "\n".join(sections)
        
        # Categorize claims by confidence and support
        supported_claims = [c for c in analysis.claims if c.overall_status.value == "supported"]
        contradicted_claims = [c for c in analysis.claims if c.overall_status.value == "contradicted"]
        unknown_claims = [c for c in analysis.claims if c.overall_status.value == "unknown"]
        
        sections.append(f"**Total Claims Analyzed**: {len(analysis.claims)}")
        sections.append(f"- ✅ **Supported**: {len(supported_claims)} claims have implementation evidence")
        sections.append(f"- ❌ **Contradicted**: {len(contradicted_claims)} claims lack supporting implementation")
        sections.append(f"- ❓ **Unknown**: {len(unknown_claims)} claims require manual verification")
        
        # Confidence distribution
        high_confidence_claims = [c for c in analysis.claims if c.confidence_score >= 0.8]
        sections.append(f"- 🎯 **High Confidence**: {len(high_confidence_claims)} claims (≥80% confidence)")
        
        # Detail top supported claims
        if supported_claims:
            sections.append("\n### ✅ Verified Implementation Claims")
            
            # Sort by confidence
            top_supported = sorted(supported_claims, key=lambda c: c.confidence_score, reverse=True)
            
            for claim in top_supported[:5]:
                sections.append(f"\n**Claim**: \"{claim.claim_text}\"")
                sections.append(f"**Confidence**: {claim.confidence_score:.0%}")
                sections.append(f"**Category**: {claim.category}")
                
                if claim.supporting_evidence:
                    evidence = claim.supporting_evidence[0]
                    if evidence.source_locations:
                        loc = evidence.source_locations[0]
                        sections.append(f"**Implementation**: `{loc.file_path}:{loc.line_start}`")
                    
                    if evidence.reasoning_chain:
                        sections.append(f"**Verification**: {evidence.reasoning_chain[0]}")
        
        # Detail contradicted claims
        if contradicted_claims:
            sections.append("\n### ❌ Implementation Gaps")
            
            for claim in contradicted_claims[:3]:
                sections.append(f"\n**Gap**: \"{claim.claim_text}\"")
                sections.append(f"**Issue**: No supporting implementation detected")
                sections.append(f"**Recommendation**: Either implement claimed functionality or update documentation")
                
                if claim.contradicting_evidence:
                    evidence = claim.contradicting_evidence[0]
                    if evidence.reasoning_chain:
                        sections.append(f"**Analysis**: {evidence.reasoning_chain[0]}")
        
        return "\n".join(sections)
    
    def _generate_architecture_education(self, analysis: AnalysisEvidence) -> str:
        """Generate educational architecture analysis"""
        
        sections = ["## Software Architecture Education\n"]
        
        sections.append("### Architectural Patterns Demonstrated")
        
        # Identify patterns from evidence
        api_evidence = [e for e in analysis.all_evidence if 'endpoint' in e.claim.lower() or 'route' in e.claim.lower()]
        class_evidence = [e for e in analysis.all_evidence if 'class' in e.claim.lower()]
        function_evidence = [e for e in analysis.all_evidence if 'function' in e.claim.lower()]
        
        if api_evidence:
            sections.append("#### REST API Architecture")
            sections.append(f"**Evidence**: {len(api_evidence)} API endpoints detected")
            sections.append("**Pattern**: HTTP-based service interface following RESTful principles")
            sections.append("**Educational Value**: Demonstrates separation between interface and implementation")
        
        if class_evidence:
            sections.append("\n#### Object-Oriented Design")
            sections.append(f"**Evidence**: {len(class_evidence)} class definitions")
            sections.append("**Pattern**: Encapsulation of data and behavior into cohesive units")
            sections.append("**Educational Value**: Shows abstraction and data modeling techniques")
        
        if analysis.mechanisms:
            sections.append("\n#### Implementation Mechanisms")
            for mechanism in analysis.mechanisms:
                sections.append(f"**Mechanism**: {mechanism.claim_id}")
                sections.append(f"**Entry Points**: {len(mechanism.entry_points)} components")
                sections.append(f"**Educational Value**: Illustrates how high-level capabilities map to code")
        
        # Civic technology patterns
        civic_evidence = [e for e in analysis.all_evidence 
                         if any(civic_word in e.claim.lower() 
                               for civic_word in ['investigation', 'pattern', 'transparency', 'accountability', 'evidence'])]
        
        if len(civic_evidence) > 10:
            sections.append("\n#### Civic Technology Architecture")
            sections.append(f"**Evidence**: {len(civic_evidence)} civic technology components")
            sections.append("**Pattern**: Evidence-first design with institutional accountability")
            sections.append("**Educational Value**: Demonstrates software architecture for public interest")
            sections.append("**Key Principles**:")
            sections.append("- Transparency through open verification")
            sections.append("- Evidence trails for institutional credibility")
            sections.append("- Cryptographic verification for adversarial environments")
        
        return "\n".join(sections)
    
    def _generate_credibility_assessment(self, analysis: AnalysisEvidence) -> str:
        """Generate institutional credibility assessment"""
        
        sections = ["## Institutional Credibility Assessment\n"]
        
        # Calculate credibility metrics
        crypto_evidence_count = self._count_crypto_evidence(analysis.all_evidence)
        verification_evidence = [e for e in analysis.all_evidence if 'verify' in e.claim.lower()]
        evidence_trail_items = [e for e in analysis.all_evidence 
                               if any(trail_word in e.claim.lower() 
                                     for trail_word in ['evidence', 'proof', 'receipt', 'audit', 'trail'])]
        
        credibility_score = self._calculate_credibility_score(analysis)
        
        sections.append(f"### Overall Credibility Score: {credibility_score}/100\n")
        
        # Assessment categories
        sections.append("#### Verification Capabilities")
        if crypto_evidence_count >= 5:
            sections.append("✅ **Strong**: Comprehensive cryptographic verification system")
        elif crypto_evidence_count >= 3:
            sections.append("⚠️ **Moderate**: Some cryptographic verification present")
        else:
            sections.append("❌ **Weak**: Limited or no cryptographic verification")
        
        sections.append(f"**Evidence**: {crypto_evidence_count} cryptographic components detected")
        
        sections.append("\n#### Evidence Trail Quality")
        if len(evidence_trail_items) >= 10:
            sections.append("✅ **Strong**: Comprehensive evidence trail implementation")
        elif len(evidence_trail_items) >= 5:
            sections.append("⚠️ **Moderate**: Basic evidence tracking present")
        else:
            sections.append("❌ **Weak**: Limited evidence trail capabilities")
        
        sections.append(f"**Evidence**: {len(evidence_trail_items)} evidence trail components")
        
        sections.append("\n#### Documentation Quality")
        doc_implementation_ratio = len(analysis.claims) / max(len(analysis.all_evidence), 1)
        if doc_implementation_ratio >= 0.3:
            sections.append("✅ **Strong**: Well-documented capabilities")
        elif doc_implementation_ratio >= 0.1:
            sections.append("⚠️ **Moderate**: Adequate documentation")
        else:
            sections.append("❌ **Weak**: Limited documentation")
        
        sections.append(f"**Evidence**: {len(analysis.claims)} documented claims vs {len(analysis.all_evidence)} implementation items")
        
        # Institutional recommendations
        sections.append("\n#### Institutional Suitability")
        
        if credibility_score >= 80:
            sections.append("**Assessment**: Suitable for adversarial institutional review")
            sections.append("**Recommendation**: Ready for external audit and verification")
        elif credibility_score >= 60:
            sections.append("**Assessment**: Suitable for collaborative institutional review")
            sections.append("**Recommendation**: Consider additional verification mechanisms")
        else:
            sections.append("**Assessment**: Requires enhancement for institutional use")
            sections.append("**Recommendation**: Implement cryptographic verification and evidence trails")
        
        return "\n".join(sections)
    
    def _generate_recommendations(self, analysis: AnalysisEvidence) -> str:
        """Generate actionable recommendations"""
        
        sections = ["## Recommendations and Next Steps\n"]
        
        recommendations = []
        
        # Cryptographic recommendations
        crypto_count = self._count_crypto_evidence(analysis.all_evidence)
        if crypto_count < 3:
            recommendations.append({
                'priority': 'High',
                'category': 'Security',
                'action': 'Implement cryptographic verification system',
                'rationale': 'Enable institutional credibility through verifiable evidence'
            })
        
        # Documentation recommendations
        if len(analysis.contradictions) > 20:
            recommendations.append({
                'priority': 'Medium',
                'category': 'Documentation',
                'action': 'Align documentation with implementation',
                'rationale': f'{len(analysis.contradictions)} potential gaps detected between claims and code'
            })
        
        # Evidence trail recommendations
        evidence_trail_count = len([e for e in analysis.all_evidence 
                                   if any(word in e.claim.lower() for word in ['evidence', 'proof', 'receipt'])])
        if evidence_trail_count < 5:
            recommendations.append({
                'priority': 'High',
                'category': 'Accountability',
                'action': 'Implement comprehensive evidence trails',
                'rationale': 'Enable external verification and audit capabilities'
            })
        
        # Testing recommendations
        if analysis.coverage_percentage < 90:
            recommendations.append({
                'priority': 'Medium',
                'category': 'Quality',
                'action': 'Improve analysis coverage',
                'rationale': f'Current coverage at {analysis.coverage_percentage:.0f}%, target 90%+'
            })
        
        # Present recommendations
        for i, rec in enumerate(recommendations, 1):
            sections.append(f"### Recommendation {i}: {rec['action']}")
            sections.append(f"**Priority**: {rec['priority']}")
            sections.append(f"**Category**: {rec['category']}")
            sections.append(f"**Rationale**: {rec['rationale']}")
            sections.append("")
        
        # Implementation guidance
        sections.append("### Implementation Guidance")
        sections.append("1. **Prioritize high-priority security and accountability recommendations**")
        sections.append("2. **Implement changes incrementally with verification at each step**")
        sections.append("3. **Re-run Code View analysis to validate improvements**")
        sections.append("4. **Consider independent security review for cryptographic implementations**")
        
        return "\n".join(sections)
    
    def _generate_technical_appendix(self, analysis: AnalysisEvidence) -> str:
        """Generate technical appendix with full evidence details"""
        
        sections = ["## Technical Appendix\n"]
        
        # Analysis metadata
        sections.append("### Analysis Metadata")
        sections.append(f"- **Repository**: {analysis.repository_url}")
        sections.append(f"- **Commit**: {analysis.commit_hash}")
        sections.append(f"- **Analysis Engine**: Code View v1.0 Enhanced")
        sections.append(f"- **Analysis Date**: {analysis.analysis_started.isoformat()}")
        if analysis.analysis_duration is not None:
            sections.append(f"- **Duration**: {analysis.analysis_duration:.2f} seconds")
        else:
            sections.append("- **Duration**: n/a")
        sections.append(f"- **Coverage**: {analysis.coverage_percentage:.1f}%")
        
        # Stage completion details
        sections.append("\n### Analysis Pipeline Results")
        sections.append("**Completed Stages**:")
        for stage in analysis.stages_completed:
            sections.append(f"- ✅ {stage}")
        
        if analysis.stages_failed:
            sections.append("\n**Failed Stages**:")
            for stage in analysis.stages_failed:
                sections.append(f"- ❌ {stage}")
        
        # Evidence distribution
        sections.append("\n### Evidence Distribution")
        
        evidence_by_confidence = {
            'high': len([e for e in analysis.all_evidence if e.confidence.value == 'high']),
            'medium': len([e for e in analysis.all_evidence if e.confidence.value == 'medium']),
            'low': len([e for e in analysis.all_evidence if e.confidence.value == 'low'])
        }
        
        sections.append("**By Confidence Level**:")
        for level, count in evidence_by_confidence.items():
            percentage = (count / len(analysis.all_evidence)) * 100 if analysis.all_evidence else 0
            sections.append(f"- {level.title()}: {count} items ({percentage:.0f}%)")
        
        # File coverage
        source_files = set()
        for evidence in analysis.all_evidence:
            for location in evidence.source_locations:
                source_files.add(location.file_path)
        
        sections.append(f"\n### Source File Coverage")
        sections.append(f"**Files Analyzed**: {len(source_files)}")
        
        # Verification information
        sections.append("\n### Verification Information")
        sections.append("This analysis can be independently verified by:")
        sections.append("1. **Re-running Code View** on the same commit hash")
        sections.append("2. **Manual source code inspection** at provided file locations")
        sections.append("3. **Cross-referencing claims** against documented capabilities")
        sections.append("4. **Cryptographic verification** of any signed analysis results")
        
        return "\n".join(sections)
    
    # Helper methods
    
    def _extract_repo_name(self, url: str) -> str:
        """Extract repository name from URL"""
        if "/" in url:
            return url.split("/")[-1].replace(".git", "")
        return url
    
    def _count_crypto_evidence(self, evidence_items: List[EvidenceItem]) -> int:
        """Count cryptographic evidence items"""
        return len([e for e in evidence_items 
                   if any(crypto_word in e.claim.lower() 
                         for crypto_word in ['crypto', 'sign', 'verify', 'hash', 'ed25519', 'receipt', 'proof'])])
    
    def _classify_system_type(self, evidence_items: List[EvidenceItem]) -> str:
        """Classify the type of system based on evidence"""
        
        framework_scores = {
            'Web API': len([e for e in evidence_items if any(w in e.claim.lower() for w in ['api', 'endpoint', 'route', 'fastapi', 'flask'])]),
            'Data Processing': len([e for e in evidence_items if any(w in e.claim.lower() for w in ['process', 'analyze', 'transform', 'pipeline'])]),
            'Civic Technology': len([e for e in evidence_items if any(w in e.claim.lower() for w in ['investigation', 'transparency', 'accountability', 'civic'])]),
            'Cryptographic System': len([e for e in evidence_items if any(w in e.claim.lower() for w in ['crypto', 'sign', 'verify', 'hash'])])
        }
        
        return max(framework_scores, key=framework_scores.get)
    
    def _get_educational_patterns(self, analysis: AnalysisEvidence) -> str:
        """Get educational patterns from the analysis"""
        
        patterns = []
        
        if self._count_crypto_evidence(analysis.all_evidence) >= 3:
            patterns.append("cryptographic verification patterns")
        
        if len([e for e in analysis.all_evidence if 'api' in e.claim.lower()]) >= 3:
            patterns.append("REST API architecture")
        
        if len([e for e in analysis.all_evidence if any(w in e.claim.lower() for w in ['investigation', 'civic'])]) >= 5:
            patterns.append("civic technology design patterns")
        
        if len(analysis.mechanisms) >= 2:
            patterns.append("layered software architecture")
        
        return ", ".join(patterns) if patterns else "standard software development practices"
    
    def _calculate_trust_score(self, analysis: AnalysisEvidence) -> int:
        """Calculate institutional trust score"""
        
        score = 50  # Base score
        
        # Boost for crypto evidence
        crypto_count = self._count_crypto_evidence(analysis.all_evidence)
        score += min(crypto_count * 8, 30)
        
        # Boost for high confidence evidence
        high_conf_ratio = len([e for e in analysis.all_evidence if e.confidence.value == 'high']) / max(len(analysis.all_evidence), 1)
        score += int(high_conf_ratio * 20)
        
        # Penalty for many contradictions
        if len(analysis.contradictions) > 20:
            score -= 15
        elif len(analysis.contradictions) > 10:
            score -= 10
        
        return min(max(score, 0), 100)
    
    def _get_trust_explanation(self, score: int, analysis: AnalysisEvidence) -> str:
        """Get explanation for trust score"""
        
        if score >= 80:
            return "**High institutional trust** - Strong cryptographic verification with comprehensive evidence trails"
        elif score >= 60:
            return "**Moderate institutional trust** - Some verification mechanisms present, suitable for collaborative review"
        elif score >= 40:
            return "**Limited institutional trust** - Basic implementation with minimal verification capabilities"
        else:
            return "**Low institutional trust** - Requires significant enhancement for institutional credibility"
    
    def _calculate_credibility_score(self, analysis: AnalysisEvidence) -> int:
        """Calculate institutional credibility score"""
        
        score = 40  # Base score
        
        # Cryptographic verification
        crypto_count = self._count_crypto_evidence(analysis.all_evidence)
        score += min(crypto_count * 6, 25)
        
        # Evidence trail quality
        evidence_trail_count = len([e for e in analysis.all_evidence 
                                   if any(word in e.claim.lower() for word in ['evidence', 'proof', 'receipt', 'audit'])])
        score += min(evidence_trail_count * 3, 20)
        
        # Documentation quality
        if analysis.claims:
            doc_quality = len([c for c in analysis.claims if c.confidence_score >= 0.7]) / len(analysis.claims)
            score += int(doc_quality * 15)
        
        return min(score, 100)

def generate_educational_dossier(analysis: AnalysisEvidence, educational: bool = True) -> str:
    """Generate comprehensive educational forensic dossier."""
    generator = EducationalDossierGenerator()
    return generator.generate_comprehensive_dossier(analysis, educational)


def generate_comparative_educational_dossier(
    analyses: List[AnalysisEvidence], educational: bool = True
) -> str:
    """Comparative markdown dossier across multiple analyzed repositories."""
    if not analyses:
        return "# Comparative Forensic Analysis\n\nNo analyses provided.\n"

    sections: List[str] = []

    repo_names = [
        analysis.repository_url.split("/")[-1].replace(".git", "") for analysis in analyses
    ]
    sections.append(f"# Comparative Forensic Analysis: {', '.join(repo_names)}")
    sections.append(
        f"**Analysis Date:** {analyses[0].analysis_started.strftime('%Y-%m-%d %H:%M UTC')}"
    )
    sections.append(f"**Platforms Compared:** {len(analyses)}\n")

    sections.append("## Executive Summary\n")
    sections.append(
        "| Platform | Evidence Items | Claims | Contradictions | Crypto Components | Trust Score |"
    )
    sections.append(
        "|----------|----------------|--------|----------------|-------------------|-------------|"
    )

    for analysis in analyses:
        repo_name = analysis.repository_url.split("/")[-1].replace(".git", "")
        crypto_count = len(
            [
                e
                for e in analysis.all_evidence
                if any(w in e.claim.lower() for w in ["crypto", "sign", "verify", "hash"])
            ]
        )
        trust_score = min(50 + crypto_count * 8 + len(analysis.mechanisms) * 10, 100)
        sections.append(
            f"| {repo_name} | {len(analysis.all_evidence)} | {len(analysis.claims)} | "
            f"{len(analysis.contradictions)} | {crypto_count} | {trust_score} |"
        )

    sections.append("\n## Comparative Analysis\n")

    best_crypto = max(
        analyses,
        key=lambda a: len([e for e in a.all_evidence if "crypto" in e.claim.lower()]),
    )
    best_name = best_crypto.repository_url.split("/")[-1].replace(".git", "")
    sections.append(f"### Most Cryptographically Sophisticated (heuristic): {best_name}")
    crypto_evidence_count = len([e for e in best_crypto.all_evidence if "crypto" in e.claim.lower()])
    sections.append(f"- **Cryptographic keyword hits:** {crypto_evidence_count}")
    sections.append(f"- **Total Evidence:** {len(best_crypto.all_evidence)}")
    sections.append(f"- **Claims Documented:** {len(best_crypto.claims)}")

    if educational:
        sections.append("\n### Educational Insights")
        sections.append("This comparative view highlights patterns across codebases:")
        sections.append("- **Evidence-first architecture** may appear across civic platforms")
        sections.append("- **Cryptographic verification** as a credibility mechanism (verify claims manually)")
        sections.append("- **Transparency** through reproducible analysis runs")

    sections.append("\n## Individual Platform Analysis\n")

    for analysis in analyses:
        repo_name = analysis.repository_url.split("/")[-1].replace(".git", "")
        sections.append(f"### {repo_name}")
        mini = generate_educational_dossier(analysis, False)
        lines = mini.split("\n")
        in_summary = False
        summary_lines: List[str] = []
        for line in lines:
            if line.startswith("## Executive Summary"):
                in_summary = True
                continue
            if line.startswith("## ") and in_summary:
                break
            if in_summary:
                summary_lines.append(line)
        sections.extend(summary_lines[:15])
        sections.append("")

    return "\n".join(sections)
