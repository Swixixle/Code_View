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


def _package_name_for_relative_imports(module_qn: str, rel_path: str) -> list[str]:
    """Package path as segments for resolving PEP 328 relative imports."""
    rel = rel_path.replace("\\", "/")
    parts = module_qn.split(".")
    if rel.endswith("__init__.py"):
        return parts
    if len(parts) <= 1:
        return []
    return parts[:-1]


def _absolute_module_for_importfrom(module_qn: str, rel_path: str, node: ast.ImportFrom) -> str | None:
    """Resolve ImportFrom to an absolute dotted module name (before ``.name`` suffix for symbols)."""
    level = getattr(node, "level", 0) or 0
    mod = node.module or ""
    pkg = _package_name_for_relative_imports(module_qn, rel_path)
    if level == 0:
        return mod if mod else None
    if level > len(pkg):
        return None
    anchor = pkg[: len(pkg) - level + 1]
    rest = mod.split(".") if mod else []
    return ".".join(anchor + rest)


def _resolve_via_package_init(
    repo_root: Path,
    abs_package_module: str,
    symbol: str,
    qns: set[str],
    *,
    _seen: set[tuple[str, str]] | None = None,
) -> str | None:
    """Follow ``package.__init__`` re-exports so ``from pkg.sub import sym`` maps to defining qual."""
    if _seen is None:
        _seen = set()
    key = (abs_package_module, symbol)
    if key in _seen:
        return None
    _seen.add(key)
    init_rel = abs_package_module.replace(".", "/") + "/__init__.py"
    p = repo_root / init_rel
    if not p.is_file():
        return None
    tree = _read_ast(p)
    if not tree:
        return None
    try:
        rp = p.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None
    sub_aliases = _module_level_import_aliases(
        tree,
        qns,
        module_qn=abs_package_module,
        rel_path=rp,
        repo_root=repo_root,
        _reexport_seen=_seen,
    )
    return sub_aliases.get(symbol)


def _module_level_import_aliases(
    tree: ast.AST,
    qns: set[str],
    *,
    module_qn: str,
    rel_path: str,
    repo_root: Path | None = None,
    _reexport_seen: set[tuple[str, str]] | None = None,
) -> dict[str, str]:
    """Map local name -> imported entity qualified name (module-level imports only)."""
    aliases: dict[str, str] = {}
    for n in getattr(tree, "body", []):
        if isinstance(n, ast.ImportFrom):
            abs_mod = _absolute_module_for_importfrom(module_qn, rel_path, n)
            for alias in n.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                level = getattr(n, "level", 0) or 0
                if abs_mod is None and level > 0 and not n.module:
                    pkg = _package_name_for_relative_imports(module_qn, rel_path)
                    if level > len(pkg):
                        continue
                    anchor = pkg[: len(pkg) - level + 1]
                    cand = ".".join(anchor + [alias.name])
                    if cand in qns:
                        aliases[local] = cand
                    continue
                if not abs_mod:
                    continue
                cand = f"{abs_mod}.{alias.name}"
                if cand in qns:
                    aliases[local] = cand
                elif repo_root is not None:
                    resolved = _resolve_via_package_init(
                        repo_root,
                        abs_mod,
                        alias.name,
                        qns,
                        _seen=_reexport_seen or set(),
                    )
                    if resolved:
                        aliases[local] = resolved
        elif isinstance(n, ast.Import):
            for alias in n.names:
                pub = alias.name
                askey = alias.asname or pub.split(".")[0]
                if pub in qns:
                    aliases[askey] = pub
                else:
                    parts = pub.split(".")
                    for i in range(len(parts), 0, -1):
                        cand = ".".join(parts[:i])
                        if cand in qns:
                            aliases[askey] = cand
                            break
    return aliases


def _resolve_call_callee(
    name: str,
    *,
    module_qn: str,
    class_stack: list[str],
    qns: set[str],
) -> tuple[str | None, str]:
    """
    Resolve a simple Name() call target. Prefer module-level symbol over class method
    so `helper()` inside a method resolves to `module.helper` when that entity exists.
    Returns (qualified_name_or_none, confidence).
    """
    if name in ("True", "False", "None"):
        return None, "low"
    mod_fn = f"{module_qn}.{name}"
    if mod_fn in qns:
        return mod_fn, "high"
    if class_stack:
        cls_fn = f"{class_stack[-1]}.{name}"
        if cls_fn in qns:
            return cls_fn, "high"
    return None, "low"


class _CallVisitor(ast.NodeVisitor):
    def __init__(
        self,
        *,
        module_qn: str,
        module_globals: set[str],
        qns: set[str],
        import_aliases: dict[str, str],
        calls_out: list[tuple[str, str | None, str]],
    ) -> None:
        self.module_qn = module_qn
        self.module_globals = module_globals
        self.qns = qns
        self.import_aliases = import_aliases
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
            callee, conf = _resolve_call_callee(
                node.func.id,
                module_qn=self.module_qn,
                class_stack=self._class_stack,
                qns=self.qns,
            )
            if callee is None and node.func.id in self.import_aliases:
                cand = self.import_aliases[node.func.id]
                if cand in self.qns:
                    callee = cand
                    conf = "high"
            if callee is None:
                conf = "low"
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id in self.module_globals:
                cand = f"{self.module_qn}.{node.func.value.id}.{node.func.attr}"
                if cand in self.qns:
                    callee = cand
                    conf = "high"
                else:
                    callee = None
                    conf = "low"
            else:
                callee = None
                conf = "low"

        self.calls_out.append((caller, callee, conf))
        self.generic_visit(node)


class _ScopedImportVisitor(ast.NodeVisitor):
    """Module- and nested-scope import -> target edges (entity-level source when resolvable)."""

    def __init__(self, module_qn: str, qns: set[str], out: list[RelationDraft]) -> None:
        self.module_qn = module_qn
        self.qns = qns
        self.out = out
        self._scope_stack: list[str] = [module_qn]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        fq = f"{self._scope_stack[-1]}.{node.name}"
        self._scope_stack.append(fq)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        fq = f"{self._scope_stack[-1]}.{node.name}"
        self._scope_stack.append(fq)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        fq = f"{self._scope_stack[-1]}.{node.name}"
        self._scope_stack.append(fq)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        src = self._scope_stack[-1]
        if src not in self.qns:
            return
        scope_tag = "module" if src == self.module_qn else "nested"
        for alias in node.names:
            pub = alias.name
            if pub in self.qns:
                self.out.append(
                    RelationDraft(
                        source_qual=src,
                        target_qual=pub,
                        relation_type="imports",
                        confidence="high",
                        evidence={"kind": "import", "name": pub, "scope": scope_tag},
                    )
                )
            else:
                parts = pub.split(".")
                for i in range(len(parts), 0, -1):
                    cand = ".".join(parts[:i])
                    if cand in self.qns:
                        self.out.append(
                            RelationDraft(
                                source_qual=src,
                                target_qual=cand,
                                relation_type="imports",
                                confidence="medium",
                                evidence={"kind": "import_prefix", "name": pub, "scope": scope_tag},
                            )
                        )
                        break

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        src = self._scope_stack[-1]
        if src not in self.qns:
            return
        base = node.module or ""
        scope_tag = "module" if src == self.module_qn else "nested"
        for alias in node.names:
            if alias.name == "*":
                continue
            if not base:
                continue
            cand = f"{base}.{alias.name}"
            if cand in self.qns:
                self.out.append(
                    RelationDraft(
                        source_qual=src,
                        target_qual=cand,
                        relation_type="imports",
                        confidence="high",
                        evidence={
                            "kind": "from",
                            "module": base,
                            "name": alias.name,
                            "scope": scope_tag,
                        },
                    )
                )
            elif base in self.qns:
                self.out.append(
                    RelationDraft(
                        source_qual=src,
                        target_qual=base,
                        relation_type="imports",
                        confidence="low",
                        evidence={
                            "kind": "from_pkg",
                            "module": base,
                            "name": alias.name,
                            "scope": scope_tag,
                        },
                    )
                )


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

    reexport_seen: set[tuple[str, str]] = set()
    root = repo_root.resolve()

    for path in iter_python_files(repo_root):
        tree = _read_ast(path)
        if not tree:
            continue
        try:
            rel = path.resolve().relative_to(root).as_posix()
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

        for n in tree.body:
            if isinstance(n, ast.Import):
                for alias in n.names:
                    pub = alias.name
                    asname = alias.asname or pub.split(".")[0]
                    globals_names.add(asname)
            elif isinstance(n, ast.ImportFrom):
                for alias in n.names:
                    if alias.name == "*":
                        continue
                    globals_names.add(alias.asname or alias.name)

        _ScopedImportVisitor(module_qn, qns, drafts).visit(tree)

        import_aliases = _module_level_import_aliases(
            tree,
            qns,
            module_qn=module_qn,
            rel_path=rel,
            repo_root=root,
            _reexport_seen=reexport_seen,
        )
        calls_raw: list[tuple[str, str | None, str]] = []
        cv = _CallVisitor(
            module_qn=module_qn,
            module_globals=globals_names,
            qns=qns,
            import_aliases=import_aliases,
            calls_out=calls_raw,
        )
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
