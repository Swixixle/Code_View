"""Static contains, import, and call edges with confidence labels."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analysis.archaeology.extractor import ExtractedEntity, iter_python_files


@dataclass
class RelationDraft:
    source_qual: str
    target_qual: str | None
    relation_type: str
    confidence: str
    evidence: dict[str, Any]


def _read_ast(path: Path) -> ast.AST | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        return ast.parse(raw, filename=str(path))
    except (OSError, SyntaxError):
        return None


def _module_qual_from_rel(rel: str) -> str:
    p = rel.replace("\\", "/")
    if p.endswith(".py"):
        p = p[:-3]
    if p.endswith("/__init__"):
        p = p[: -len("/__init__")]
    return p.replace("/", ".")


def _resolve_qual_name(
    name: str,
    *,
    module_qn: str,
    class_stack: list[str],
    module_globals: set[str],
) -> str | None:
    if name in ("True", "False", "None"):
        return None
    if class_stack:
        return f"{class_stack[-1]}.{name}"
    if name in module_globals:
        return f"{module_qn}.{name}"
    return None


class _CallVisitor(ast.NodeVisitor):
    def __init__(
        self,
        *,
        module_qn: str,
        module_globals: set[str],
        calls_out: list[tuple[str, str | None, str]],
    ) -> None:
        self.module_qn = module_qn
        self.module_globals = module_globals
        self.calls_out = calls_out
        self._class_stack: list[str] = []
        self._func_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        qual = f"{self.module_qn}.{node.name}"
        self._class_stack.append(qual)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_func(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_func(node, is_async=True)

    def _visit_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_async: bool) -> None:
        if self._class_stack:
            fq = f"{self._class_stack[-1]}.{node.name}"
        else:
            fq = f"{self.module_qn}.{node.name}"
        self._func_stack.append(fq)
        self.generic_visit(node)
        self._func_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        caller = self._func_stack[-1] if self._func_stack else None
        if not caller:
            self.generic_visit(node)
            return

        callee: str | None = None
        conf = "low"
        if isinstance(node.func, ast.Name):
            callee = _resolve_qual_name(
                node.func.id,
                module_qn=self.module_qn,
                class_stack=self._class_stack,
                module_globals=self.module_globals,
            )
            conf = "medium" if callee else "low"
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id in self.module_globals:
                callee = f"{self.module_qn}.{node.func.value.id}.{node.func.attr}"
                conf = "medium"
            else:
                callee = None
                conf = "low"

        self.calls_out.append((caller, callee, conf))
        self.generic_visit(node)


def collect_relations(
    repo_root: Path,
    entities: list[ExtractedEntity],
) -> list[RelationDraft]:
    """Build contains, imports, and call relations."""
    qual_to_kind = {e.qualified_name: e.entity_kind for e in entities}
    qns = set(qual_to_kind)

    drafts: list[RelationDraft] = []

    for e in entities:
        if e.parent_qualified_name and e.parent_qualified_name in qns:
            drafts.append(
                RelationDraft(
                    source_qual=e.parent_qualified_name,
                    target_qual=e.qualified_name,
                    relation_type="contains",
                    confidence="high",
                    evidence={"reason": "AST parent span"},
                )
            )

    for path in iter_python_files(repo_root):
        tree = _read_ast(path)
        if not tree:
            continue
        try:
            rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            continue
        module_qn = _module_qual_from_rel(rel)

        mod_entity = next((x for x in entities if x.qualified_name == module_qn and x.entity_kind == "module"), None)
        if not mod_entity:
            continue

        globals_names: set[str] = set()
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                globals_names.add(n.name)
            elif isinstance(n, ast.ClassDef):
                globals_names.add(n.name)
            elif isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        globals_names.add(t.id)

        def _maybe_import_edge(target_qn: str, confidence: str, extra: dict) -> None:
            if target_qn not in qns:
                return
            drafts.append(
                RelationDraft(
                    source_qual=module_qn,
                    target_qual=target_qn,
                    relation_type="imports",
                    confidence=confidence,
                    evidence=extra,
                )
            )

        for n in tree.body:
            if isinstance(n, ast.Import):
                for alias in n.names:
                    pub = alias.name
                    asname = alias.asname or pub.split(".")[0]
                    globals_names.add(asname)
                    if pub in qns:
                        _maybe_import_edge(pub, "high", {"kind": "import", "name": pub})
                    else:
                        parts = pub.split(".")
                        for i in range(len(parts), 0, -1):
                            cand = ".".join(parts[:i])
                            if cand in qns:
                                _maybe_import_edge(cand, "medium", {"kind": "import_prefix", "name": pub})
                                break
            elif isinstance(n, ast.ImportFrom):
                base = n.module or ""
                for alias in n.names:
                    if alias.name == "*":
                        continue
                    globals_names.add(alias.asname or alias.name)
                    if not base:
                        continue
                    cand = f"{base}.{alias.name}"
                    if cand in qns:
                        _maybe_import_edge(cand, "high", {"kind": "from", "module": base, "name": alias.name})
                    elif base in qns:
                        _maybe_import_edge(base, "low", {"kind": "from_pkg", "module": base, "name": alias.name})

        calls_raw: list[tuple[str, str | None, str]] = []
        cv = _CallVisitor(module_qn=module_qn, module_globals=globals_names, calls_out=calls_raw)
        cv.visit(tree)

        for caller, callee, conf in calls_raw:
            if callee and callee in qns:
                drafts.append(
                    RelationDraft(
                        source_qual=caller,
                        target_qual=callee,
                        relation_type="calls",
                        confidence=conf,
                        evidence={"static_resolution": True},
                    )
                )

    seen: set[tuple[str, str, str]] = set()
    unique: list[RelationDraft] = []
    for d in drafts:
        if not d.target_qual:
            continue
        key = (d.source_qual, d.target_qual, d.relation_type)
        if key in seen:
            continue
        seen.add(key)
        unique.append(d)
    return unique
