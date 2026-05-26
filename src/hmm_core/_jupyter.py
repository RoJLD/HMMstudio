"""HTML rendering helpers for Jupyter rich displays (Phase I.1).

All major classes get a ``_repr_html_()`` method that produces a nicely
formatted HTML representation when displayed in Jupyter / IPython / VS Code
notebooks / Colab.

Design choice : **pure HTML + inline CSS, zero JavaScript, zero external
dependencies**. This means rich displays render reliably everywhere, even
in environments that block scripts. Trade-off : no live interactivity
(animations, hover tooltips) — those are reserved for the standalone web
UI. Notebook users get static-but-rich representations.

The shared helpers below are imported by each domain class's
``_repr_html_`` method ; the class itself focuses on what to display.
"""

from __future__ import annotations

import html
from typing import Sequence

import numpy as np


# ---------------------------------------------------------------------------
# Inline CSS shared by every _repr_html_
# ---------------------------------------------------------------------------

_CSS = """<style>
.hmm-studio {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 760px;
  color: #222;
  margin: 8px 0;
}
.hmm-studio h4 { color: #1a1a1a; margin: 6px 0; font-size: 14px; }
.hmm-studio h5 { color: #555; margin: 12px 0 4px 0; font-size: 12px; font-weight: 600; }
.hmm-studio table { border-collapse: collapse; margin: 4px 0; font-size: 12px; }
.hmm-studio th, .hmm-studio td {
  padding: 3px 8px; text-align: center; border: 1px solid #e0e0e0;
}
.hmm-studio th { background: #f5f5f5; font-weight: 600; color: #333; }
.hmm-studio .label { color: #666; font-weight: normal; text-align: left; }
.hmm-studio .value { color: #111; text-align: left; }
.hmm-studio .stats-table td { border: none; padding: 2px 8px; }
.hmm-studio .stats-table { background: #fafafa; border: 1px solid #e8e8e8;
                            border-radius: 4px; padding: 4px 8px; }
.hmm-studio .forbidden { color: #aaa; background: #f5f5f5; font-style: italic; }
.hmm-studio .ok { color: #2a7a2a; font-weight: 600; }
.hmm-studio .warn { color: #b07000; }
.hmm-studio .err { color: #a02020; font-weight: 600; }
.hmm-studio .small { font-size: 11px; color: #777; }
.hmm-studio code { font-family: 'SF Mono', Consolas, monospace;
                   background: #f3f3f3; padding: 1px 4px; border-radius: 3px;
                   font-size: 11px; }
</style>"""


# ---------------------------------------------------------------------------
# Primitive renderers
# ---------------------------------------------------------------------------


def _esc(s) -> str:
    return html.escape(str(s))


def _color_for_value(v: float, max_val: float = 1.0) -> str:
    """Map ``v`` ∈ [0, max_val] to a CSS background color (white → deep blue)."""
    if not np.isfinite(v) or max_val <= 0:
        return "#f0f0f0"
    intensity = float(min(1.0, max(0.0, v / max_val)))
    r = int(255 - 255 * intensity)
    g = int(255 - 155 * intensity)
    b = int(255 - 55 * intensity)
    return f"rgb({r},{g},{b})"


def _text_color_for_bg(v: float, max_val: float = 1.0) -> str:
    if not np.isfinite(v) or max_val <= 0:
        return "black"
    intensity = float(min(1.0, max(0.0, v / max_val)))
    return "white" if intensity > 0.55 else "black"


def render_stats_table(rows: Sequence[tuple[str, object]]) -> str:
    """Render a 2-column key-value table (label → value)."""
    body = []
    for label, value in rows:
        body.append(
            f'<tr><td class="label">{_esc(label)}</td>'
            f'<td class="value">{_esc(value)}</td></tr>'
        )
    return (
        '<table class="stats-table"><tbody>'
        + "".join(body)
        + "</tbody></table>"
    )


def render_matrix_heatmap(
    matrix: np.ndarray,
    row_labels: Sequence[str],
    col_labels: Sequence[str],
    *,
    forbidden_mask: np.ndarray | None = None,
    precision: int = 3,
    title: str | None = None,
) -> str:
    """Render a 2D matrix as an HTML heatmap with row/column labels.

    Parameters
    ----------
    matrix
        Shape (R, C). NaN cells render as gray.
    row_labels, col_labels
        Header labels.
    forbidden_mask
        Optional (R, C) bool. Cells where mask is False render as a gray ``×``
        regardless of the underlying value (useful for transmat with mask).
    precision
        Decimals shown in each cell.
    title
        Optional <h5> above the table.
    """
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError(f"matrix must be 2D, got shape {matrix.shape}")

    finite_vals = matrix[np.isfinite(matrix)]
    max_val = float(finite_vals.max()) if finite_vals.size > 0 else 1.0

    out = []
    if title:
        out.append(f"<h5>{_esc(title)}</h5>")
    out.append("<table>")
    header_cells = ["<th></th>"] + [f"<th>{_esc(lbl)}</th>" for lbl in col_labels]
    out.append("<tr>" + "".join(header_cells) + "</tr>")
    for i, row_lbl in enumerate(row_labels):
        cells = [f"<th>{_esc(row_lbl)}</th>"]
        for j in range(matrix.shape[1]):
            if forbidden_mask is not None and not forbidden_mask[i, j]:
                cells.append('<td class="forbidden">×</td>')
            else:
                v = matrix[i, j]
                bg = _color_for_value(v, max_val)
                fg = _text_color_for_bg(v, max_val)
                if np.isnan(v):
                    cells.append('<td style="background: #f0f0f0; color: #999">—</td>')
                else:
                    cells.append(
                        f'<td style="background: {bg}; color: {fg}">{v:.{precision}f}</td>'
                    )
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</table>")
    return "".join(out)


def render_sequence_strip(
    sequence: np.ndarray,
    *,
    max_display: int = 80,
    palette: Sequence[str] | None = None,
    title: str | None = None,
) -> str:
    """Render an integer sequence (e.g. Viterbi path) as a colored strip.

    Used by FittedModel._repr_html_ to give a visual sense of the decoded
    state trajectory. Truncates long sequences and indicates the truncation.
    """
    sequence = np.asarray(sequence)
    if palette is None:
        # 12 distinguishable colors (Tableau / colorblind-friendly-ish)
        palette = [
            "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948",
            "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac", "#5b9bd5", "#a5a5a5",
        ]
    pal = list(palette)

    n = len(sequence)
    if n == 0:
        return '<div class="small">(empty sequence)</div>'

    truncated = n > max_display
    show = sequence[:max_display] if truncated else sequence

    cells = []
    for s in show:
        color = pal[int(s) % len(pal)]
        cells.append(
            f'<span title="state {int(s)}" '
            f'style="display:inline-block;width:8px;height:18px;'
            f'background:{color};margin-right:1px"></span>'
        )

    out = []
    if title:
        out.append(f"<h5>{_esc(title)}</h5>")
    out.append('<div style="white-space:nowrap;line-height:0">' + "".join(cells) + "</div>")
    if truncated:
        out.append(
            f'<div class="small">… truncated, showing {max_display} of {n} steps</div>'
        )
    return "".join(out)


def render_chip_list(items: Sequence[str], *, kind: str = "chip") -> str:
    """Render a list of strings as inline pill-style chips."""
    if not items:
        return '<span class="small">(none)</span>'
    chip_css = (
        "display:inline-block;background:#eef;color:#225;padding:2px 6px;"
        "margin:1px;border-radius:10px;font-size:11px"
    )
    return "".join(
        f'<span style="{chip_css}">{_esc(item)}</span>' for item in items
    )


def wrap_html(*parts: str) -> str:
    """Wrap one or more HTML fragments in the .hmm-studio container + CSS."""
    return '<div class="hmm-studio">' + _CSS + "".join(parts) + "</div>"
