"""
Code View - Enhanced Python Parser with Cryptographic Detection
Detects Ed25519, hashing, and security implementations
"""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional

from dataclasses import dataclass

from models.evidence import (
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStatus,
    EvidenceType,
    ExtractedSymbol,
    SourceLocation,
)

from analysis.parsers.python_parser import PythonASTParser, _display_path

@dataclass
class CryptographicFunction:
    name: str
    function_type: str  # sign, verify, hash, encrypt, decrypt, keygen
    library: str
    lineno: int
    file_path: str
    algorithm: Optional[str] = None
    signature: Optional[str] = None

@dataclass
class SecurityBoundary:
    name: str
    boundary_type: str  # auth, signature, validation, encryption
    lineno: int
    file_path: str
    verification_method: Optional[str] = None

class EnhancedPythonParser(PythonASTParser):
    """Enhanced Python parser with cryptographic and security detection"""
    
    def __init__(self):
        super().__init__()
        self.crypto_functions: List[CryptographicFunction] = []
        self.security_boundaries: List[SecurityBoundary] = []
        self.hash_operations: List[Dict] = []
        self.signature_operations: List[Dict] = []
        
        # Cryptographic library patterns
        self.crypto_libraries = {
            'cryptography': ['ed25519', 'rsa', 'aes', 'sha256', 'sha512'],
            'nacl': ['signing', 'verify', 'secretbox', 'box'],
            'hashlib': ['sha256', 'sha512', 'md5', 'blake2b'],
            'ecdsa': ['signingkey', 'verifyingkey', 'sign', 'verify'],
            'pycryptodome': ['aes', 'rsa', 'sha256'],
            'jwcrypto': ['jwk', 'jws', 'jwt'],
            'coincurve': ['privatekey', 'publickey']
        }
        
        # Security function patterns
        self.security_patterns = {
            'signing': ['sign', 'signature', 'ed25519', 'ecdsa'],
            'verification': ['verify', 'validate', 'check_signature'],
            'hashing': ['hash', 'digest', 'sha256', 'blake2'],
            'encryption': ['encrypt', 'decrypt', 'cipher', 'aes'],
            'authentication': ['auth', 'login', 'token', 'jwt'],
            'receipt': ['receipt', 'proof', 'attestation', 'witness']
        }
    
    def parse_file(
        self, file_path: Path, repo_root: Optional[Path] = None
    ) -> List[EvidenceItem]:
        """Enhanced parsing with cryptographic detection."""
        self.clear()

        display_path = _display_path(file_path, repo_root)
        evidence_items: List[EvidenceItem] = []

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            self._extract_functions(tree, display_path, content)
            self._extract_classes(tree, display_path, content)
            self._extract_imports(tree, display_path)
            self._extract_routes(tree, display_path, content)

            self._extract_crypto_functions(tree, display_path, content)
            self._extract_security_boundaries(tree, display_path, content)
            self._extract_hash_operations(tree, display_path, content)
            self._extract_signature_operations(tree, display_path, content)

            evidence_items.extend(self._functions_to_evidence())
            evidence_items.extend(self._classes_to_evidence())
            evidence_items.extend(self._routes_to_evidence())
            evidence_items.extend(self._imports_to_evidence())

            evidence_items.extend(self._crypto_functions_to_evidence())
            evidence_items.extend(self._security_boundaries_to_evidence())
            evidence_items.extend(self._hash_operations_to_evidence())
            evidence_items.extend(self._signature_operations_to_evidence())

        except Exception as e:  # noqa: BLE001
            evidence_items.append(
                EvidenceItem(
                    claim=f"Failed to parse {file_path.name}: {str(e)}",
                    status=EvidenceStatus.UNKNOWN,
                    evidence_type=EvidenceType.NOT_VERIFIED,
                    confidence=ConfidenceLevel.LOW,
                    source_locations=[SourceLocation(file_path=display_path, line_start=1)],
                    reasoning_chain=[f"Parsing error: {str(e)}"],
                    analysis_stage="enhanced_python_parsing",
                )
            )

        return evidence_items
    
    def _extract_crypto_functions(self, tree: ast.AST, file_path: str, content: str):
        """Extract cryptographic functions and operations"""
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name.lower()
                
                # Check function name for cryptographic patterns
                crypto_type = self._identify_crypto_function_type(func_name)
                if crypto_type:
                    library = self._identify_crypto_library_from_function(node, content)
                    algorithm = self._identify_algorithm(func_name, node, content)
                    
                    crypto_func = CryptographicFunction(
                        name=node.name,
                        function_type=crypto_type,
                        library=library,
                        lineno=node.lineno,
                        file_path=file_path,
                        algorithm=algorithm,
                        signature=f"{node.name}({', '.join([arg.arg for arg in node.args.args])})"
                    )
                    self.crypto_functions.append(crypto_func)
            
            # Check function calls for crypto operations
            elif isinstance(node, ast.Call):
                if hasattr(node.func, 'attr'):
                    method_name = node.func.attr.lower()
                    crypto_type = self._identify_crypto_function_type(method_name)
                    if crypto_type:
                        library = self._get_call_library(node)
                        
                        crypto_func = CryptographicFunction(
                            name=method_name,
                            function_type=crypto_type,
                            library=library,
                            lineno=node.lineno,
                            file_path=file_path
                        )
                        self.crypto_functions.append(crypto_func)
    
    def _extract_security_boundaries(self, tree: ast.AST, file_path: str, content: str):
        """Extract security boundaries and trust boundaries"""
        
        for node in ast.walk(tree):
            # Look for decorator-based security boundaries
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    boundary_type = self._identify_security_boundary(decorator)
                    if boundary_type:
                        boundary = SecurityBoundary(
                            name=node.name,
                            boundary_type=boundary_type,
                            lineno=node.lineno,
                            file_path=file_path,
                            verification_method=self._extract_verification_method(node, content)
                        )
                        self.security_boundaries.append(boundary)
            
            # Look for explicit verification calls
            elif isinstance(node, ast.Call):
                if self._is_verification_call(node):
                    boundary = SecurityBoundary(
                        name=self._get_call_name(node),
                        boundary_type="verification",
                        lineno=node.lineno,
                        file_path=file_path
                    )
                    self.security_boundaries.append(boundary)
    
    def _extract_hash_operations(self, tree: ast.AST, file_path: str, content: str):
        """Extract hashing operations and digest functions"""
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if self._is_hash_operation(node):
                    hash_op = {
                        'function': self._get_call_name(node),
                        'algorithm': self._extract_hash_algorithm(node),
                        'lineno': node.lineno,
                        'file_path': file_path
                    }
                    self.hash_operations.append(hash_op)
    
    def _extract_signature_operations(self, tree: ast.AST, file_path: str, content: str):
        """Extract digital signature operations"""
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node).lower()
                
                # Ed25519 signatures
                if any(pattern in call_name for pattern in ['sign', 'verify', 'ed25519']):
                    sig_op = {
                        'operation': 'sign' if 'sign' in call_name else 'verify',
                        'algorithm': 'ed25519' if 'ed25519' in call_name else 'unknown',
                        'function': self._get_call_name(node),
                        'lineno': node.lineno,
                        'file_path': file_path
                    }
                    self.signature_operations.append(sig_op)
    
    def _identify_crypto_function_type(self, func_name: str) -> Optional[str]:
        """Identify the type of cryptographic function"""
        func_lower = func_name.lower()
        
        if any(pattern in func_lower for pattern in ['sign', 'signature']):
            return 'signing'
        elif any(pattern in func_lower for pattern in ['verify', 'validate']):
            return 'verification'
        elif any(pattern in func_lower for pattern in ['hash', 'digest', 'sha']):
            return 'hashing'
        elif any(pattern in func_lower for pattern in ['encrypt', 'cipher']):
            return 'encryption'
        elif any(pattern in func_lower for pattern in ['decrypt']):
            return 'decryption'
        elif any(pattern in func_lower for pattern in ['keygen', 'generate_key']):
            return 'key_generation'
        elif any(pattern in func_lower for pattern in ['receipt', 'proof', 'attest']):
            return 'receipt_generation'
        
        return None
    
    def _identify_crypto_library_from_function(self, node: ast.FunctionDef, content: str) -> str:
        """Identify which cryptographic library is being used"""
        
        # Check imports in the function
        func_start = node.lineno
        func_end = getattr(node, 'end_lineno', func_start + 10)
        
        lines = content.split('\n')[func_start-1:func_end]
        func_content = '\n'.join(lines).lower()
        
        for library, patterns in self.crypto_libraries.items():
            if library in func_content or any(pattern in func_content for pattern in patterns):
                return library
        
        return 'unknown'
    
    def _identify_algorithm(self, func_name: str, node: ast.FunctionDef, content: str) -> Optional[str]:
        """Identify the cryptographic algorithm being used"""
        
        func_name_lower = func_name.lower()
        
        if 'ed25519' in func_name_lower:
            return 'Ed25519'
        elif any(alg in func_name_lower for alg in ['sha256', 'sha512']):
            return 'SHA-256' if 'sha256' in func_name_lower else 'SHA-512'
        elif 'blake2' in func_name_lower:
            return 'BLAKE2'
        elif 'rsa' in func_name_lower:
            return 'RSA'
        
        # Check function body for algorithm hints
        try:
            func_start = node.lineno
            func_end = getattr(node, 'end_lineno', func_start + 20)
            lines = content.split('\n')[func_start-1:func_end]
            func_content = '\n'.join(lines).lower()
            
            if 'ed25519' in func_content:
                return 'Ed25519'
            elif 'sha256' in func_content:
                return 'SHA-256'
            elif 'blake2' in func_content:
                return 'BLAKE2'
        except:
            pass
        
        return None
    
    def _identify_security_boundary(self, decorator: ast.expr) -> Optional[str]:
        """Identify security boundary types from decorators"""
        
        decorator_name = self._get_decorator_name(decorator).lower()
        
        if any(pattern in decorator_name for pattern in ['auth', 'login', 'token']):
            return 'authentication'
        elif any(pattern in decorator_name for pattern in ['sign', 'signature']):
            return 'signature_verification'
        elif any(pattern in decorator_name for pattern in ['validate', 'verify']):
            return 'input_validation'
        elif any(pattern in decorator_name for pattern in ['secure', 'protect']):
            return 'access_control'
        
        return None
    
    def _is_verification_call(self, node: ast.Call) -> bool:
        """Check if a function call is a verification operation"""
        call_name = self._get_call_name(node).lower()
        return any(pattern in call_name for pattern in ['verify', 'validate', 'check_signature'])
    
    def _is_hash_operation(self, node: ast.Call) -> bool:
        """Check if a function call is a hash operation"""
        call_name = self._get_call_name(node).lower()
        return any(pattern in call_name for pattern in ['hash', 'digest', 'sha256', 'blake2'])
    
    def _get_call_name(self, node: ast.Call) -> str:
        """Extract the name of a function call"""
        if hasattr(node.func, 'attr'):
            return node.func.attr
        elif hasattr(node.func, 'id'):
            return node.func.id
        else:
            return 'unknown_call'
    
    def _get_call_library(self, node: ast.Call) -> str:
        """Extract the library name from a function call"""
        if hasattr(node.func, 'value') and hasattr(node.func.value, 'id'):
            return node.func.value.id
        return 'unknown'
    
    def _extract_verification_method(self, node: ast.FunctionDef, content: str) -> Optional[str]:
        """Extract verification method details from function"""
        try:
            func_start = node.lineno
            func_end = getattr(node, 'end_lineno', func_start + 10)
            lines = content.split('\n')[func_start-1:func_end]
            func_content = '\n'.join(lines).lower()
            
            if 'ed25519' in func_content:
                return 'Ed25519_signature'
            elif 'jwt' in func_content:
                return 'JWT_token'
            elif 'hash' in func_content:
                return 'hash_verification'
            
        except:
            pass
        
        return None
    
    def _extract_hash_algorithm(self, node: ast.Call) -> str:
        """Extract hash algorithm from call"""
        call_name = self._get_call_name(node).lower()
        
        if 'sha256' in call_name:
            return 'SHA-256'
        elif 'sha512' in call_name:
            return 'SHA-512'
        elif 'blake2' in call_name:
            return 'BLAKE2'
        elif 'md5' in call_name:
            return 'MD5'
        
        return 'unknown'
    
    # Evidence conversion methods
    
    def _crypto_functions_to_evidence(self) -> List[EvidenceItem]:
        """Convert cryptographic functions to evidence items"""
        evidence_items = []
        
        if not self.crypto_functions:
            return evidence_items
        
        # Group by type
        signing_funcs = [f for f in self.crypto_functions if f.function_type == 'signing']
        verification_funcs = [f for f in self.crypto_functions if f.function_type == 'verification']
        hashing_funcs = [f for f in self.crypto_functions if f.function_type == 'hashing']
        
        # Evidence for signing capabilities
        if signing_funcs:
            algorithms = list({f.algorithm for f in signing_funcs if f.algorithm})
            evidence_items.append(EvidenceItem(
                claim=f"Cryptographic signing implemented with {', '.join(algorithms) if algorithms else 'unknown algorithms'}",
                status=EvidenceStatus.SUPPORTED,
                evidence_type=EvidenceType.EXTRACTED,
                confidence=ConfidenceLevel.HIGH,
                source_locations=[
                    SourceLocation(file_path=f.file_path, line_start=f.lineno) 
                    for f in signing_funcs[:3]
                ],
                extracted_symbols=[
                    ExtractedSymbol(
                        name=f.name,
                        type="crypto_signing_function",
                        location=SourceLocation(file_path=f.file_path, line_start=f.lineno),
                        signature=f.signature
                    ) for f in signing_funcs[:3]
                ],
                reasoning_chain=[
                    f"Found {len(signing_funcs)} signing functions",
                    f"Algorithms detected: {algorithms}" if algorithms else "Algorithm detection needed",
                    f"Libraries used: {list(set(f.library for f in signing_funcs))}"
                ],
                analysis_stage="cryptographic_analysis"
            ))
        
        # Evidence for verification capabilities
        if verification_funcs:
            evidence_items.append(EvidenceItem(
                claim="Cryptographic signature verification implemented",
                status=EvidenceStatus.SUPPORTED,
                evidence_type=EvidenceType.EXTRACTED,
                confidence=ConfidenceLevel.HIGH,
                source_locations=[
                    SourceLocation(file_path=f.file_path, line_start=f.lineno) 
                    for f in verification_funcs[:3]
                ],
                extracted_symbols=[
                    ExtractedSymbol(
                        name=f.name,
                        type="crypto_verification_function",
                        location=SourceLocation(file_path=f.file_path, line_start=f.lineno)
                    ) for f in verification_funcs[:3]
                ],
                reasoning_chain=[
                    f"Found {len(verification_funcs)} verification functions",
                    "Signature verification ensures data integrity"
                ],
                analysis_stage="cryptographic_analysis"
            ))
        
        return evidence_items
    
    def _security_boundaries_to_evidence(self) -> List[EvidenceItem]:
        """Convert security boundaries to evidence items"""
        evidence_items = []
        
        if not self.security_boundaries:
            return evidence_items
        
        # Group by boundary type
        boundary_types = {}
        for boundary in self.security_boundaries:
            if boundary.boundary_type not in boundary_types:
                boundary_types[boundary.boundary_type] = []
            boundary_types[boundary.boundary_type].append(boundary)
        
        for boundary_type, boundaries in boundary_types.items():
            evidence_items.append(EvidenceItem(
                claim=f"Security boundary: {boundary_type} protection implemented",
                status=EvidenceStatus.SUPPORTED,
                evidence_type=EvidenceType.EXTRACTED,
                confidence=ConfidenceLevel.HIGH,
                source_locations=[
                    SourceLocation(file_path=b.file_path, line_start=b.lineno) 
                    for b in boundaries[:3]
                ],
                reasoning_chain=[
                    f"Found {len(boundaries)} {boundary_type} boundaries",
                    "Security boundaries enforce trust assumptions"
                ],
                analysis_stage="security_analysis"
            ))
        
        return evidence_items
    
    def _hash_operations_to_evidence(self) -> List[EvidenceItem]:
        """Convert hash operations to evidence items"""
        evidence_items = []
        
        if not self.hash_operations:
            return evidence_items
        
        algorithms = list(set(op['algorithm'] for op in self.hash_operations))
        
        evidence_items.append(EvidenceItem(
            claim=f"Cryptographic hashing implemented: {', '.join(algorithms)}",
            status=EvidenceStatus.SUPPORTED,
            evidence_type=EvidenceType.EXTRACTED,
            confidence=ConfidenceLevel.HIGH,
            source_locations=[
                SourceLocation(file_path=op['file_path'], line_start=op['lineno'])
                for op in self.hash_operations[:3]
            ],
            reasoning_chain=[
                f"Found {len(self.hash_operations)} hash operations",
                f"Hash algorithms: {algorithms}",
                "Hashing provides data integrity verification"
            ],
            analysis_stage="cryptographic_analysis"
        ))
        
        return evidence_items
    
    def _signature_operations_to_evidence(self) -> List[EvidenceItem]:
        """Convert signature operations to evidence items"""
        evidence_items = []
        
        if not self.signature_operations:
            return evidence_items
        
        sign_ops = [op for op in self.signature_operations if op['operation'] == 'sign']
        verify_ops = [op for op in self.signature_operations if op['operation'] == 'verify']
        algorithms = list(set(op['algorithm'] for op in self.signature_operations if op['algorithm'] != 'unknown'))
        
        if sign_ops or verify_ops:
            evidence_items.append(EvidenceItem(
                claim=f"Digital signature system: {', '.join(algorithms) if algorithms else 'unknown algorithm'}",
                status=EvidenceStatus.SUPPORTED,
                evidence_type=EvidenceType.EXTRACTED,
                confidence=ConfidenceLevel.HIGH if algorithms else ConfidenceLevel.MEDIUM,
                source_locations=[
                    SourceLocation(file_path=op['file_path'], line_start=op['lineno'])
                    for op in (sign_ops + verify_ops)[:3]
                ],
                reasoning_chain=[
                    f"Found {len(sign_ops)} signing operations",
                    f"Found {len(verify_ops)} verification operations",
                    f"Signature algorithms: {algorithms}" if algorithms else "Algorithm detection needed",
                    "Digital signatures provide authenticity and non-repudiation"
                ],
                analysis_stage="cryptographic_analysis"
            ))
        
        return evidence_items
    
    def clear(self):
        """Clear all parsed data including crypto data"""
        super().clear()
        self.crypto_functions.clear()
        self.security_boundaries.clear()
        self.hash_operations.clear()
        self.signature_operations.clear()

def parse_python_directory_enhanced(directory_path: Path) -> List[EvidenceItem]:
    """Parse all Python files with cryptographic and security heuristics."""
    parser = EnhancedPythonParser()
    root = directory_path.resolve()
    all_evidence: List[EvidenceItem] = []

    python_files = list(directory_path.rglob("*.py"))
    filtered_files: List[Path] = []
    for file_path in python_files:
        if not any(
            excluded in file_path.parts
            for excluded in (".venv", "venv", "__pycache__", ".git", "node_modules", "build", "dist")
        ):
            filtered_files.append(file_path)

    for file_path in filtered_files:
        try:
            all_evidence.extend(parser.parse_file(file_path, repo_root=root))
        except Exception as e:  # noqa: BLE001
            disp = _display_path(file_path, root)
            all_evidence.append(
                EvidenceItem(
                    claim=f"Could not parse {file_path.name}",
                    status=EvidenceStatus.UNKNOWN,
                    evidence_type=EvidenceType.NOT_VERIFIED,
                    confidence=ConfidenceLevel.LOW,
                    source_locations=[SourceLocation(file_path=disp, line_start=1)],
                    reasoning_chain=[f"Parse error: {str(e)}"],
                    analysis_stage="enhanced_python_parsing",
                )
            )

    if filtered_files:
        all_evidence.append(
            EvidenceItem(
                claim=f"Python codebase contains {len(filtered_files)} source files (enhanced scan)",
                status=EvidenceStatus.SUPPORTED,
                evidence_type=EvidenceType.EXTRACTED,
                confidence=ConfidenceLevel.HIGH,
                source_locations=[
                    SourceLocation(file_path=_display_path(f, root), line_start=1) for f in filtered_files[:5]
                ],
                reasoning_chain=[
                    f"Found {len(filtered_files)} Python files",
                    "Enhanced pass includes cryptographic and security boundary heuristics",
                ],
                analysis_stage="python_ast_parsing",
            )
        )

    crypto_evidence = [
        e
        for e in all_evidence
        if "crypto" in e.claim.lower()
        or "sign" in e.claim.lower()
        or "hash" in e.claim.lower()
        or e.analysis_stage in ("cryptographic_analysis", "security_analysis", "cryptographic_summary")
    ]
    if crypto_evidence:
        all_evidence.append(
            EvidenceItem(
                claim=f"Cryptographic/security-related signals: {len(crypto_evidence)} evidence items",
                status=EvidenceStatus.SUPPORTED,
                evidence_type=EvidenceType.INFERRED,
                confidence=ConfidenceLevel.MEDIUM,
                reasoning_chain=[
                    f"Heuristic count of crypto/security-related evidence: {len(crypto_evidence)}",
                    "Review extracted symbols and claims for Ed25519, hashing, and auth boundaries",
                ],
                analysis_stage="cryptographic_summary",
            )
        )

    return all_evidence
