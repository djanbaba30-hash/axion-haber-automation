"""Düzeltme çağrısı neyi değiştirdi: kelime düzeyinde fark (silinen üstü çizili kırmızı, eklenen yeşil)."""

from __future__ import annotations

import difflib
import html

STYLE = ("<style>.fark{line-height:1.6;font-size:15px}.fark del{background:#FDECEA;color:#9B1C1C}"
         ".fark ins{background:#E6F4EC;color:#14532D;text-decoration:none}</style>")


def word_diff_html(old: str, new: str) -> str:
    before, after = old.split(), new.split()
    parts: list[str] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=before, b=after, autojunk=False).get_opcodes():
        if tag in ("delete", "replace"):
            parts.append(f"<del>{html.escape(' '.join(before[i1:i2]))}</del>")
        if tag in ("insert", "replace"):
            parts.append(f"<ins>{html.escape(' '.join(after[j1:j2]))}</ins>")
        if tag == "equal":
            parts.append(html.escape(" ".join(before[i1:i2])))
    return '<div class="fark">' + " ".join(parts) + "</div>"


def changed_fields(first: dict[str, str], final: dict[str, str]) -> dict[str, tuple[str, str]]:
    return {name: (first[name], final[name]) for name in first if first[name] != final.get(name, first[name])}
