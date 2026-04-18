"""Python AST extraction: modules, classes, functions, methods, routes."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from analysis.archaeology.hashes import (
    content_hash_from_source,
    sha256_hex,
    signature_hash_for_class,
    signature_hash_for_function,
    structural_hash_for_node,
)


SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        "build",
        "dist",
        ".eggs",
        "*.egg-info",
    }
)


def _should_skip_dir(path: Path) -> bool:
    name = path.name
    if name in SKIP_DIR_NAMES:
        return True
    if name.endswith(".egg-info"):
        return True
    return False


HTTP_ROUTE_ATTRS = frozenset(
    {"get", "post", "put", "delete", "patch", "head", "options", "route", "api_route", "websocket"}
)


def _decorator_is_route(dec: ast.expr) -> bool:
    if isinstance(dec, ast.Call):
        fn = dec.func
    else:
        fn = dec
    if isinstance(fn, ast.Attribute) and fn.attr.lower() in HTTP_ROUTE_ATTRS:
        return True
    if isinstance(fn, ast.Name) and fn.id in ("route", "websocket"):
        return True
    return False


@dataclass
class ExtractedEntity:
    """In-memory entity before persistence."""

    qualified_name: str
    symbol_name: str
    entity_kind: str
    file_path: str
    start_line: int
    end_line: int
    parent_qualified_name: str | None
    content_hash: str
    signature_hash: str
    structural_hash: str
    docstring: str | None
    raw_content: str
    normalized_content: str


@dataclass
class ExtractionBundle:
    repo_root: Path
    entities: list[ExtractedEntity] = field(default_factory=list)
    files_scanned: int = 0


def _rel_file_path(repo_root: Path, file_path: Path) -> str:
    try:
        return file_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return file_path.as_posix()


def _module_qual_name(rel_path: str) -> str:
    p = rel_path.replace("\\", "/")
    if p.endswith(".py"):
        p = p[:-3]
    if p.endswith("/__init__"):
        p = p[: -len("/__init__")]
    return p.replace("/", ".")


def _extract_route_meta(dec_list: list[ast.expr]) -> str | None:
    for dec in dec_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if not isinstance(target, ast.Attribute):
            continue
        if target.attr.lower() not in HTTP_ROUTE_ATTRS:
            continue
        if isinstance(dec, ast.Call) and dec.args:
            try:
                return ast.unparse(dec.args[0])
            except Exception:  # noqa: BLE001
                return "route"
        return "route"
    return None


class _EntityExtractor(ast.NodeVisitor):
    def __init__(
        self,
        *,
        repo_root: Path,
        file_path: Path,
        module_qn: str,
        source: str,
        lines: list[str],
    ) -> None:
        self.repo_root = repo_root
        self.file_path = file_path
        self.rel_file = _rel_file_path(repo_root, file_path)
        self.module_qn = module_qn
        self.source = source
        self.lines = lines
        self.entities: list[ExtractedEntity] = []
        self._class_stack: list[str] = []

    def _snippet(self, node: ast.AST) -> str:
        start = node.lineno - 1
        end = (node.end_lineno or node.lineno) - 1
        chunk = self.lines[start : end + 1]
        return "\n".join(chunk)

    def _add(
        self,
        *,
        kind: str,
        qual_name: str,
        sym: str,
        node: ast.AST,
        parent_qn: str | None,
        content_hash: str,
        sig_hash: str,
        struct_hash: str,
        doc: str | None,
    ) -> None:
        start = node.lineno
        end = node.end_lineno or node.lineno
        raw = self._snippet(node)
        norm = " ".join(raw.split())
        self.entities.append(
            ExtractedEntity(
                qualified_name=qual_name,
                symbol_name=sym,
                entity_kind=kind,
                file_path=self.rel_file,
                start_line=start,
                end_line=end,
                parent_qualified_name=parent_qn,
                content_hash=content_hash,
                signature_hash=sig_hash,
                structural_hash=struct_hash,
                docstring=doc,
                raw_content=raw,
                normalized_content=norm,
            )
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        doc = ast.get_docstring(node)
        sig = signature_hash_for_class(node.name, node.bases, node.decorator_list)
        struct = structural_hash_for_node(node)
        cnt = content_hash_from_source(self._snippet(node))
        qual = f"{self.module_qn}.{node.name}" if self.module_qn else node.name
        parent = self._class_stack[-1] if self._class_stack else self.module_qn
        self._add(
            kind="class",
            qual_name=qual,
            sym=node.name,
            node=node,
            parent_qn=parent,
            content_hash=cnt,
            sig_hash=sig,
            struct_hash=struct,
            doc=doc,
        )
        self._class_stack.append(qual)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function(node, is_async=True)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_async: bool) -> None:
        doc = ast.get_docstring(node)
        sig = signature_hash_for_function(
            node.name, node.args, node.returns, node.decorator_list, is_async
        )
        struct = structural_hash_for_node(node)
        cnt = content_hash_from_source(self._snippet(node))
        is_route = any(_decorator_is_route(d) for d in node.decorator_list)

        if self._class_stack:
            qual = f"{self._class_stack[-1]}.{node.name}"
            parent = self._class_stack[-1]
            kind: str = "method"
        else:
            qual = f"{self.module_qn}.{node.name}" if self.module_qn else node.name
            parent = self.module_qn
            kind = "function"

        if is_route and not self._class_stack:
            route_qual = qual + ":route"
            route_meta = _extract_route_meta(list(node.decorator_list)) or "route"
            sig_r = sha256_hex(f"route|{route_meta}|{sig}")
            self._add(
                kind="route",
                qual_name=route_qual,
                sym=node.name,
                node=node,
                parent_qn=parent,
                content_hash=cnt,
                sig_hash=sig_r,
                struct_hash=struct,
                doc=doc,
            )
        else:
            self._add(
                kind=kind,
                qual_name=qual,
                sym=node.name,
                node=node,
                parent_qn=parent,
                content_hash=cnt,
                sig_hash=sig,
                struct_hash=struct,
                doc=doc,
            )
        self.generic_visit(node)


def extract_from_file(repo_root: Path, file_path: Path) -> list[ExtractedEntity]:
    raw = file_path.read_text(encoding="utf-8", errors="replace")
    rel = _rel_file_path(repo_root, file_path)
    module_qn = _module_qual_name(rel)
    lines = raw.splitlines()
    try:
        tree = ast.parse(raw, filename=str(file_path))
    except SyntaxError:
        return []

    mod_start, mod_end_line = 1, max(len(lines), 1)
    module_src = "\n".join(lines[mod_start - 1 : mod_end_line])
    mod_content = content_hash_from_source(module_src)
    mod_struct = structural_hash_for_node(tree)

    entities: list[ExtractedEntity] = [
        ExtractedEntity(
            qualified_name=module_qn,
            symbol_name=module_qn.split(".")[-1] if "." in module_qn else module_qn,
            entity_kind="module",
            file_path=rel,
            start_line=mod_start,
            end_line=mod_end_line,
            parent_qualified_name=None,
            content_hash=mod_content,
            signature_hash=sha256_hex(f"module|{module_qn}"),
            structural_hash=mod_struct,
            docstring=ast.get_docstring(tree),
            raw_content=module_src,
            normalized_content=" ".join(module_src.split()),
        )
    ]

    vis = _EntityExtractor(
        repo_root=repo_root,
        file_path=file_path,
        module_qn=module_qn,
        source=raw,
        lines=lines,
    )
    vis.visit(tree)
    entities.extend(vis.entities)
    return entities


def extract_repository(repo_root: Path) -> ExtractionBundle:
    root = repo_root.resolve()
    bundle = ExtractionBundle(repo_root=root)
    for path in sorted(root.rglob("*.py")):
        if any(_should_skip_dir(p) for p in path.parents if p != root):
            continue
        if path.name == "setup.py" and "site-packages" in path.parts:  # extra safety
            continue
        try:
            ents = extract_from_file(root, path)
        except OSError:
            continue
        bundle.entities.extend(ents)
        bundle.files_scanned += 1
    return bundle


def iter_python_files(repo_root: Path) -> Iterator[Path]:
    root = repo_root.resolve()
    for path in sorted(root.rglob("*.py")):
        if any(_should_skip_dir(p) for p in path.parents if p != root):
            continue
        yield path
