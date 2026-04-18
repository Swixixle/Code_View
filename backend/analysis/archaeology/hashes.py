"""Deterministic triple-hash helpers for entity identity."""

from __future__ import annotations

import ast
import hashlib
import re
from itertools import zip_longest
from typing import Any


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_ws(text: str) -> str:
    return " ".join(text.split())


class _StructuralHasher(ast.NodeVisitor):
    """Collect AST shape with names/constants collapsed to placeholders."""

    def __init__(self) -> None:
        self._parts: list[str] = []

    def generic_visit(self, node: ast.AST) -> None:
        self._parts.append(type(node).__name__)
        for field, value in ast.iter_fields(node):
            if field in ("lineno", "col_offset", "end_lineno", "end_col_offset"):
                continue
            self._visit_field(value)

    def _visit_field(self, value: Any) -> None:
        if value is None:
            self._parts.append("None")
        elif isinstance(value, ast.AST):
            self.visit(value)
        elif isinstance(value, list):
            self._parts.append("[")
            for item in value:
                if isinstance(item, ast.AST):
                    self.visit(item)
                else:
                    self._parts.append(repr(type(item).__name__))
            self._parts.append("]")
        else:
            self._parts.append("_")

    def digest(self) -> str:
        return "".join(self._parts)


def structural_hash_for_node(node: ast.AST) -> str:
    h = _StructuralHasher()
    h.visit(node)
    return sha256_hex(h.digest())


def content_hash_from_source(source: str) -> str:
    return sha256_hex(normalize_ws(source))


_SIGNATURE_NOISE = re.compile(r"\s+")


def signature_hash_for_function(
    name: str,
    args: ast.arguments,
    returns: ast.expr | None,
    decorator_nodes: list[ast.expr],
    is_async: bool,
) -> str:
    try:
        ret = ast.unparse(returns) if returns else ""
    except Exception:  # noqa: BLE001
        ret = ""
    arg_parts: list[str] = []
    for a in args.posonlyargs:
        arg_parts.append(a.arg)
    if args.vararg:
        arg_parts.append("*" + args.vararg.arg)
    for a in args.args:
        arg_parts.append(a.arg)
    if args.kwonlyargs:
        for a, _d in zip_longest(args.kwonlyargs, args.kw_defaults, fillvalue=None):
            arg_parts.append(a.arg)
    if args.kwarg:
        arg_parts.append("**" + args.kwarg.arg)
    deco_strs: list[str] = []
    for d in decorator_nodes:
        try:
            deco_strs.append(ast.unparse(d))
        except Exception:  # noqa: BLE001
            deco_strs.append(type(d).__name__)
    raw = f"{'async ' if is_async else ''}{name}({','.join(arg_parts)})->{ret}|" + "|".join(
        sorted(deco_strs)
    )
    norm = _SIGNATURE_NOISE.sub(" ", raw.strip())
    return sha256_hex(norm)


def signature_hash_for_class(name: str, bases: list[ast.expr], decorator_nodes: list[ast.expr]) -> str:
    try:
        b = ",".join(sorted(ast.unparse(x) for x in bases))
    except Exception:  # noqa: BLE001
        b = ""
    deco_strs: list[str] = []
    for d in decorator_nodes:
        try:
            deco_strs.append(ast.unparse(d))
        except Exception:  # noqa: BLE001
            deco_strs.append(type(d).__name__)
    raw = f"class {name}({b})|" + "|".join(sorted(deco_strs))
    return sha256_hex(_SIGNATURE_NOISE.sub(" ", raw.strip()))


def module_content_hash(module_source: str) -> str:
    return content_hash_from_source(module_source)
