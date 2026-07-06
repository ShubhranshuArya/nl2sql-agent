"""Curated Vega-Lite v6 few-shot examples used to ground chart generation.

These minimal, correct skeletons reflect the Vega-Lite v6 grammar (matching the
frontend's `vega-lite ^6.4.2` renderer). They are injected into the generator
prompt so the LLM copies current v6 shapes instead of relying on stale memory.

Notes:
- `data` is intentionally omitted; the result rows are injected server-side.
- Every spec pins the v6 `$schema`, `width: "container"`, `height: 300`, an
  `autosize` config, tooltips, and a title placeholder.
"""

VEGA_LITE_SCHEMA_V6 = "https://vega.github.io/schema/vega-lite/v6.json"

_COMMON = {
    "$schema": VEGA_LITE_SCHEMA_V6,
    "width": "container",
    "height": 300,
    "autosize": {"type": "fit", "contains": "padding"},
}

BAR_EXAMPLE = {
    **_COMMON,
    "title": "Revenue by category",
    "mark": {"type": "bar", "tooltip": True},
    "encoding": {
        "x": {"field": "category", "type": "nominal", "sort": "-y", "axis": {"labelAngle": -45}},
        "y": {"field": "revenue", "type": "quantitative"},
        "tooltip": [
            {"field": "category", "type": "nominal"},
            {"field": "revenue", "type": "quantitative", "format": ",.0f"},
        ],
    },
}

LINE_EXAMPLE = {
    **_COMMON,
    "title": "Revenue over time",
    "mark": {"type": "line", "point": True, "tooltip": True},
    "encoding": {
        "x": {"field": "month", "type": "temporal"},
        "y": {"field": "revenue", "type": "quantitative"},
        "tooltip": [
            {"field": "month", "type": "temporal"},
            {"field": "revenue", "type": "quantitative", "format": ",.0f"},
        ],
    },
}

PIE_EXAMPLE = {
    **_COMMON,
    "title": "Share by channel",
    "mark": {"type": "arc", "tooltip": True},
    "encoding": {
        "theta": {"field": "value", "type": "quantitative", "stack": True},
        "color": {"field": "channel", "type": "nominal"},
        "tooltip": [
            {"field": "channel", "type": "nominal"},
            {"field": "value", "type": "quantitative", "format": ",.0f"},
        ],
    },
}

SCATTER_EXAMPLE = {
    **_COMMON,
    "title": "Price vs. quantity",
    "mark": {"type": "point", "tooltip": True},
    "encoding": {
        "x": {"field": "unit_price_usd", "type": "quantitative"},
        "y": {"field": "quantity", "type": "quantitative"},
        "tooltip": [
            {"field": "unit_price_usd", "type": "quantitative"},
            {"field": "quantity", "type": "quantitative"},
        ],
    },
}

VEGA_LITE_EXAMPLES = {
    "bar": BAR_EXAMPLE,
    "line": LINE_EXAMPLE,
    "pie": PIE_EXAMPLE,
    "scatter": SCATTER_EXAMPLE,
}


def get_examples(chart_type: str | None) -> dict:
    """Return the relevant few-shot example(s) for the chosen chart type.

    Falls back to all four examples when the type is unknown/None so the model
    can still pick an appropriate shape.
    """
    if chart_type in VEGA_LITE_EXAMPLES:
        return {chart_type: VEGA_LITE_EXAMPLES[chart_type]}
    return VEGA_LITE_EXAMPLES
