"""Terminal table formatting with width-aware truncation."""

from __future__ import annotations

import shutil
import textwrap
from typing import Any, Iterable


def format_table(
    rows: Iterable[dict[str, Any]],
    columns: list[str],
    max_width: int | None = None,
) -> str:
    items = list(rows)
    if not items:
        return "Nenhum registro encontrado."
    if not columns:
        return ""

    terminal_width = max_width or shutil.get_terminal_size((100, 24)).columns
    terminal_width = max(24, terminal_width)
    separators = 3 * (len(columns) - 1)
    available = max(len(columns) * 4, terminal_width - separators)

    natural = {
        column: max(len(column), *(len(_clean(row.get(column, ""))) for row in items))
        for column in columns
    }
    widths = _fit_widths(natural, columns, available)

    if sum(widths.values()) + separators > terminal_width:
        return _format_stacked(items, columns, terminal_width)

    header = " | ".join(_clip(column, widths[column]).ljust(widths[column]) for column in columns)
    separator = "-+-".join("-" * widths[column] for column in columns)
    body = [
        " | ".join(_clip(row.get(column, ""), widths[column]).ljust(widths[column]) for column in columns)
        for row in items
    ]
    return "\n".join([header, separator, *body])


def _format_stacked(rows: list[dict[str, Any]], columns: list[str], width: int) -> str:
    """Render records vertically when horizontal columns would overflow the terminal."""
    line_width = max(12, width - 2)
    records: list[str] = []
    for row in rows:
        lines: list[str] = []
        for column in columns:
            value = _clean(row.get(column, "")) or "-"
            wrapped = textwrap.wrap(
                value,
                width=max(8, line_width - len(column) - 2),
                break_long_words=True,
                break_on_hyphens=False,
            ) or ["-"]
            lines.append(f"{column}: {wrapped[0]}")
            lines.extend(f"{' ' * (len(column) + 2)}{part}" for part in wrapped[1:])
        records.append("\n".join(lines))
    return "\n".join(records)


def _fit_widths(natural: dict[str, int], columns: list[str], available: int) -> dict[str, int]:
    minimum = {column: min(max(len(column), 4), 12) for column in columns}
    widths = {column: max(minimum[column], natural[column]) for column in columns}
    total = sum(widths.values())
    if total <= available:
        return widths

    # Shrink longest columns first, never below a readable minimum.
    while sum(widths.values()) > available:
        candidates = [c for c in columns if widths[c] > minimum[c]]
        if not candidates:
            break
        longest = max(candidates, key=lambda c: widths[c])
        widths[longest] -= 1
    return widths


def _clean(value: Any) -> str:
    return " ".join(str(value if value is not None else "").split())


def _clip(value: Any, width: int) -> str:
    text = _clean(value)
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."
