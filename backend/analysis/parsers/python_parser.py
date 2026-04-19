"""
Code View - Python AST Parser
Real evidence extraction from Python source code with full provenance
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.evidence import (
    SOURCE_CLASS_CODE_DEFINITION,
    SOURCE_CLASS_CODE_RELATION,
    SOURCE_CLASS_KEYWORD_HEURISTIC,
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStatus,
    EvidenceType,
    ExtractedSymbol,
    SourceLocation,
)


@dataclass
class ParsedFunction:
    name: str
    lineno: int
    col_offset: int
    args: List[str]
    returns: Optional[str]
    decorators: List[str]
    docstring: Optional[str]
    is_async: bool
    file_path: str


@dataclass
class ParsedClass:
    name: str
    lineno: int
    col_offset: int
    bases: List[str]
    methods: List[str]
    docstring: Optional[str]
    file_path: str


@dataclass
class ParsedRoute:
    method: str
    path: str
    function_name: str
    lineno: int
    file_path: str
    decorators: List[str]


@dataclass
class ParsedImport:
    module: str
    names: List[str]
    lineno: int
    file_path: str
    is_from_import: bool


class PythonASTParser:
    """Extracts evidence from Python source files using AST analysis."""

    def __init__(self) -> None:
        self.functions: List[ParsedFunction] = []
        self.classes: List[ParsedClass] = []
        self.routes: List[ParsedRoute] = []
        self.imports: List[ParsedImport] = []
        self.variables: List[Dict[str, Any]] = []

    def parse_file(self, file_path: Path, repo_root: Optional[Path] = None) -> List[EvidenceItem]:
        """Parse a single Python file and extract evidence."""
        self.clear()

        display_path = _display_path(file_path, repo_root)

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            self._extract_functions(tree, display_path, content)
            self._extract_classes(tree, display_path, content)
            self._extract_imports(tree, display_path)
            self._extract_routes(tree, display_path, content)

            evidence_items: List[EvidenceItem] = []
            evidence_items.extend(self._functions_to_evidence())
            evidence_items.extend(self._classes_to_evidence())
            evidence_items.extend(self._routes_to_evidence())
            evidence_items.extend(self._imports_to_evidence())

        except SyntaxError as e:
            evidence_items = [
                EvidenceItem(
                    claim=f"Python syntax error in {file_path.name}",
                    status=EvidenceStatus.CONTRADICTED,
                    evidence_type=EvidenceType.EXTRACTED,
                    confidence=ConfidenceLevel.HIGH,
                    source_locations=[
                        SourceLocation(
                            file_path=display_path,
                            line_start=e.lineno or 1,
                        )
                    ],
                    reasoning_chain=[f"Syntax error: {e.msg}"],
                    analysis_stage="python_ast_parsing",
                    source_class=SOURCE_CLASS_CODE_DEFINITION,
                    derived_from_code=True,
                    derived_from_doc=False,
                    support_strength="strong",
                )
            ]
        except Exception as e:
            evidence_items = [
                EvidenceItem(
                    claim=f"Failed to parse {file_path.name}",
                    status=EvidenceStatus.UNKNOWN,
                    evidence_type=EvidenceType.NOT_VERIFIED,
                    confidence=ConfidenceLevel.LOW,
                    source_locations=[SourceLocation(file_path=display_path, line_start=1)],
                    reasoning_chain=[f"Parsing error: {str(e)}"],
                    analysis_stage="python_ast_parsing",
                    source_class=SOURCE_CLASS_KEYWORD_HEURISTIC,
                    support_strength="weak",
                )
            ]

        return evidence_items

    def _extract_functions(self, tree: ast.AST, file_path: str, content: str) -> None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [arg.arg for arg in node.args.args]
                decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]
                docstring = ast.get_docstring(node)
                returns = self._get_annotation_string(node.returns) if node.returns else None

                func = ParsedFunction(
                    name=node.name,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    args=args,
                    returns=returns,
                    decorators=decorators,
                    docstring=docstring,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    file_path=file_path,
                )
                self.functions.append(func)

    def _extract_classes(self, tree: ast.AST, file_path: str, content: str) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [self._get_name_string(base) for base in node.bases]
                methods: List[str] = []
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(child.name)

                docstring = ast.get_docstring(node)

                cls = ParsedClass(
                    name=node.name,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    bases=bases,
                    methods=methods,
                    docstring=docstring,
                    file_path=file_path,
                )
                self.classes.append(cls)

    def _extract_imports(self, tree: ast.AST, file_path: str) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imp = ParsedImport(
                        module=alias.name,
                        names=[alias.asname or alias.name],
                        lineno=node.lineno,
                        file_path=file_path,
                        is_from_import=False,
                    )
                    self.imports.append(imp)
            elif isinstance(node, ast.ImportFrom):
                names = [alias.asname or alias.name for alias in node.names]
                imp = ParsedImport(
                    module=node.module or "",
                    names=names,
                    lineno=node.lineno,
                    file_path=file_path,
                    is_from_import=True,
                )
                self.imports.append(imp)

    def _extract_routes(self, tree: ast.AST, file_path: str, content: str) -> None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    route_info = self._parse_route_decorator(decorator)
                    if route_info:
                        route = ParsedRoute(
                            method=route_info["method"],
                            path=route_info["path"],
                            function_name=node.name,
                            lineno=node.lineno,
                            file_path=file_path,
                            decorators=[self._get_decorator_name(dec) for dec in node.decorator_list],
                        )
                        self.routes.append(route)

    def _parse_route_decorator(self, decorator: ast.expr) -> Optional[Dict[str, str]]:
        if isinstance(decorator, ast.Call):
            func_name = self._get_decorator_name(decorator.func)

            if any(method in func_name.lower() for method in ["get", "post", "put", "delete", "patch"]):
                method = func_name.split(".")[-1].upper()
                if decorator.args:
                    path = _string_from_arg(decorator.args[0])
                    if path is not None:
                        return {"method": method, "path": path}

            if "route" in func_name.lower():
                path = ""
                method = "GET"

                if decorator.args:
                    p = _string_from_arg(decorator.args[0])
                    if p is not None:
                        path = p

                for keyword in decorator.keywords:
                    if keyword.arg == "methods":
                        if isinstance(keyword.value, ast.List):
                            methods = [
                                _string_from_arg(elt)
                                for elt in keyword.value.elts
                                if _string_from_arg(elt) is not None
                            ]
                            if methods:
                                method = methods[0] or method

                if path:
                    return {"method": method, "path": path}

        return None

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        if isinstance(decorator, ast.Name):
            return decorator.id
        if isinstance(decorator, ast.Attribute):
            return f"{self._get_name_string(decorator.value)}.{decorator.attr}"
        if isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return "unknown_decorator"

    def _get_name_string(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_name_string(node.value)}.{node.attr}"
        if isinstance(node, ast.Constant):
            return str(node.value)
        return "unknown"

    def _get_annotation_string(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_name_string(node.value)}.{node.attr}"
        if isinstance(node, ast.Constant):
            return str(node.value)
        return "unknown_type"

    def _functions_to_evidence(self) -> List[EvidenceItem]:
        evidence_items: List[EvidenceItem] = []
        functions_by_file: Dict[str, List[ParsedFunction]] = {}
        for func in self.functions:
            functions_by_file.setdefault(func.file_path, []).append(func)

        for file_path, funcs in functions_by_file.items():
            func_names = [f.name for f in funcs]
            async_count = len([f for f in funcs if f.is_async])

            evidence_items.append(
                EvidenceItem(
                    claim=f"Python functions implemented: {', '.join(func_names[:5])}"
                    + ("..." if len(func_names) > 5 else ""),
                    status=EvidenceStatus.SUPPORTED,
                    evidence_type=EvidenceType.EXTRACTED,
                    confidence=ConfidenceLevel.HIGH,
                    source_locations=[
                        SourceLocation(file_path=file_path, line_start=f.lineno) for f in funcs[:3]
                    ],
                    extracted_symbols=[
                        ExtractedSymbol(
                            name=f.name,
                            type="async_function" if f.is_async else "function",
                            location=SourceLocation(file_path=file_path, line_start=f.lineno),
                        )
                        for f in funcs[:3]
                    ],
                    reasoning_chain=[
                        f"Found {len(funcs)} functions in {file_path}",
                        f"{async_count} async functions detected" if async_count else "No async functions",
                    ],
                    analysis_stage="python_ast_parsing",
                    source_class=SOURCE_CLASS_CODE_DEFINITION,
                    derived_from_code=True,
                    derived_from_doc=False,
                    support_strength="strong",
                )
            )

            for func in funcs:
                if any(
                    keyword in func.name.lower()
                    for keyword in [
                        "investigate",
                        "analyze",
                        "pattern",
                        "detect",
                        "sign",
                        "verify",
                    ]
                ):
                    evidence_items.append(
                        EvidenceItem(
                            claim=f"Key function '{func.name}' implements core logic",
                            status=EvidenceStatus.SUPPORTED,
                            evidence_type=EvidenceType.EXTRACTED,
                            confidence=ConfidenceLevel.HIGH,
                            source_locations=[
                                SourceLocation(file_path=file_path, line_start=func.lineno)
                            ],
                            extracted_symbols=[
                                ExtractedSymbol(
                                    name=func.name,
                                    type="async_function" if func.is_async else "function",
                                    location=SourceLocation(file_path=file_path, line_start=func.lineno),
                                    signature=f"{func.name}({', '.join(func.args)})",
                                )
                            ],
                            reasoning_chain=[
                                f"Function name '{func.name}' suggests core functionality",
                                f"Arguments: {func.args}" if func.args else "No arguments",
                                "Docstring present" if func.docstring else "No docstring",
                            ],
                            analysis_stage="python_ast_parsing",
                            source_class=SOURCE_CLASS_CODE_DEFINITION,
                            derived_from_code=True,
                            derived_from_doc=False,
                            support_strength="strong",
                        )
                    )

        return evidence_items

    def _classes_to_evidence(self) -> List[EvidenceItem]:
        evidence_items: List[EvidenceItem] = []
        for cls in self.classes:
            evidence_items.append(
                EvidenceItem(
                    claim=f"Python class '{cls.name}' defines data model",
                    status=EvidenceStatus.SUPPORTED,
                    evidence_type=EvidenceType.EXTRACTED,
                    confidence=ConfidenceLevel.HIGH,
                    source_locations=[SourceLocation(file_path=cls.file_path, line_start=cls.lineno)],
                    extracted_symbols=[
                        ExtractedSymbol(
                            name=cls.name,
                            type="class",
                            location=SourceLocation(file_path=cls.file_path, line_start=cls.lineno),
                        )
                    ],
                    reasoning_chain=[
                        f"Class definition found: {cls.name}",
                        f"Inherits from: {cls.bases}" if cls.bases else "No inheritance",
                        f"Methods: {cls.methods}" if cls.methods else "No methods",
                    ],
                    analysis_stage="python_ast_parsing",
                    source_class=SOURCE_CLASS_CODE_DEFINITION,
                    derived_from_code=True,
                    derived_from_doc=False,
                    support_strength="strong",
                )
            )
        return evidence_items

    def _routes_to_evidence(self) -> List[EvidenceItem]:
        evidence_items: List[EvidenceItem] = []
        if self.routes:
            route_descriptions = [f"{r.method} {r.path}" for r in self.routes]
            evidence_items.append(
                EvidenceItem(
                    claim=f"API endpoints implemented: {', '.join(route_descriptions)}",
                    status=EvidenceStatus.SUPPORTED,
                    evidence_type=EvidenceType.EXTRACTED,
                    confidence=ConfidenceLevel.HIGH,
                    source_locations=[
                        SourceLocation(file_path=r.file_path, line_start=r.lineno) for r in self.routes
                    ],
                    extracted_symbols=[
                        ExtractedSymbol(
                            name=r.function_name,
                            type="route_handler",
                            location=SourceLocation(file_path=r.file_path, line_start=r.lineno),
                        )
                        for r in self.routes
                    ],
                    reasoning_chain=[
                        f"Found {len(self.routes)} API routes",
                        f"HTTP methods: {set(r.method for r in self.routes)}",
                        f"Route patterns: {[r.path for r in self.routes[:3]]}",
                    ],
                    analysis_stage="python_ast_parsing",
                    source_class=SOURCE_CLASS_CODE_DEFINITION,
                    derived_from_code=True,
                    derived_from_doc=False,
                    support_strength="strong",
                )
            )
        return evidence_items

    def _imports_to_evidence(self) -> List[EvidenceItem]:
        evidence_items: List[EvidenceItem] = []
        framework_imports: List[ParsedImport] = []
        security_imports: List[ParsedImport] = []

        for imp in self.imports:
            module_name = imp.module.lower()
            if any(framework in module_name for framework in ["fastapi", "flask", "django"]):
                framework_imports.append(imp)
            elif any(security in module_name for security in ["cryptography", "jwt", "oauth", "auth"]):
                security_imports.append(imp)

        if framework_imports:
            frameworks = list({imp.module.split(".")[0] for imp in framework_imports})
            evidence_items.append(
                EvidenceItem(
                    claim=f"Web framework detected: {', '.join(frameworks)}",
                    status=EvidenceStatus.SUPPORTED,
                    evidence_type=EvidenceType.EXTRACTED,
                    confidence=ConfidenceLevel.HIGH,
                    source_locations=[
                        SourceLocation(file_path=imp.file_path, line_start=imp.lineno)
                        for imp in framework_imports[:3]
                    ],
                    reasoning_chain=[f"Import statements for {frameworks}"],
                    analysis_stage="python_ast_parsing",
                    source_class=SOURCE_CLASS_CODE_RELATION,
                    derived_from_code=True,
                    derived_from_doc=False,
                    support_strength="moderate",
                )
            )

        if security_imports:
            security_modules = list({imp.module.split(".")[0] for imp in security_imports})
            evidence_items.append(
                EvidenceItem(
                    claim=f"Security libraries in use: {', '.join(security_modules)}",
                    status=EvidenceStatus.SUPPORTED,
                    evidence_type=EvidenceType.EXTRACTED,
                    confidence=ConfidenceLevel.HIGH,
                    source_locations=[
                        SourceLocation(file_path=imp.file_path, line_start=imp.lineno)
                        for imp in security_imports[:3]
                    ],
                    reasoning_chain=[f"Security-related imports: {security_modules}"],
                    analysis_stage="python_ast_parsing",
                    source_class=SOURCE_CLASS_CODE_RELATION,
                    derived_from_code=True,
                    derived_from_doc=False,
                    support_strength="moderate",
                )
            )

        return evidence_items

    def clear(self) -> None:
        self.functions.clear()
        self.classes.clear()
        self.routes.clear()
        self.imports.clear()
        self.variables.clear()


def _display_path(file_path: Path, repo_root: Optional[Path]) -> str:
    if repo_root is not None:
        try:
            return str(file_path.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            pass
    return str(file_path)


def _string_from_arg(node: ast.expr) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def parse_python_directory(directory_path: Path) -> List[EvidenceItem]:
    """Parse all Python files under a directory and return evidence."""
    parser = PythonASTParser()
    root = directory_path.resolve()
    all_evidence: List[EvidenceItem] = []

    python_files = list(directory_path.rglob("*.py"))
    filtered_files: List[Path] = []
    for file_path in python_files:
        parts = file_path.parts
        if not any(
            excluded in parts
            for excluded in (".venv", "venv", "__pycache__", ".git", "node_modules", "build", "dist")
        ):
            filtered_files.append(file_path)

    for file_path in filtered_files:
        try:
            evidence = parser.parse_file(file_path, repo_root=root)
            all_evidence.extend(evidence)
        except Exception as e:
            disp = _display_path(file_path, root)
            all_evidence.append(
                EvidenceItem(
                    claim=f"Could not parse {file_path.name}",
                    status=EvidenceStatus.UNKNOWN,
                    evidence_type=EvidenceType.NOT_VERIFIED,
                    confidence=ConfidenceLevel.LOW,
                    source_locations=[SourceLocation(file_path=disp, line_start=1)],
                    reasoning_chain=[f"Parse error: {str(e)}"],
                    analysis_stage="python_ast_parsing",
                    source_class=SOURCE_CLASS_KEYWORD_HEURISTIC,
                    support_strength="weak",
                )
            )

    if filtered_files:
        all_evidence.append(
            EvidenceItem(
                claim=f"Python codebase contains {len(filtered_files)} source files",
                status=EvidenceStatus.SUPPORTED,
                evidence_type=EvidenceType.EXTRACTED,
                confidence=ConfidenceLevel.HIGH,
                source_locations=[
                    SourceLocation(file_path=_display_path(f, root), line_start=1) for f in filtered_files[:5]
                ],
                reasoning_chain=[
                    f"Found {len(filtered_files)} Python files",
                    "Excluded virtual environments and build directories",
                ],
                analysis_stage="python_ast_parsing",
                source_class=SOURCE_CLASS_KEYWORD_HEURISTIC,
                derived_from_code=True,
                derived_from_doc=False,
                support_strength="moderate",
            )
        )

    return all_evidence
