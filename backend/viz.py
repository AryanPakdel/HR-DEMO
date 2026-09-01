"""سازنده‌های قرارداد پاسخ: KPI، نمودار، جدول و متن تحلیلی.

فرانت‌اند هیچ کد اختصاصی برای هیچ سؤالی ندارد؛ هر تحلیل خروجی خود را با همین
سازنده‌ها توصیف می‌کند و رندرکننده عمومی آن را نمایش می‌دهد.
"""

from __future__ import annotations

import math
from typing import Any, Iterable


def _clean(value: Any) -> Any:
    """تبدیل مقادیر numpy/NaN به مقادیر قابل سریال‌سازی در JSON."""
    if value is None:
        return None
    if isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int,)):
        return int(value)
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else round(value, 6)
    if hasattr(value, "item"):  # numpy scalar
        try:
            return _clean(value.item())
        except (ValueError, AttributeError):
            return str(value)
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return str(value)


def kpi(label: str, value: Any, fmt: str = "number", hint: str = "", tone: str = "neutral") -> dict:
    """یک کارت شاخص کلیدی.

    fmt: number | percent | days | currency | score | ratio
    tone: neutral | good | warn | bad
    """
    return {"label": label, "value": _clean(value), "format": fmt, "hint": hint, "tone": tone}


def insight(text: str, tone: str = "info", title: str = "") -> dict:
    """یک بند تحلیل متنی. tone: info | good | warn | bad"""
    return {"text": text, "tone": tone, "title": title}


def series(name: str, data: Iterable, color: str | None = None, kind: str | None = None) -> dict:
    """یک سری داده. kind برای نمودارهای ترکیبی (مثلاً خط روی ستون) استفاده می‌شود."""
    out = {"name": name, "data": [_clean(v) for v in data]}
    if color:
        out["color"] = color
    if kind:
        out["kind"] = kind
    return out


def chart(
    chart_type: str,
    title: str,
    categories: Iterable | None = None,
    series_list: list[dict] | None = None,
    *,
    subtitle: str = "",
    y_format: str = "number",
    y_label: str = "",
    x_label: str = "",
    annotations: list[dict] | None = None,
    highlight: list[int] | None = None,
    stacked: bool = False,
    options: dict | None = None,
    footnote: str = "",
) -> dict:
    """توصیف یک نمودار.

    chart_type: bar | hbar | line | area | donut | funnel | histogram | scatter | radar | heatmap
    """
    return {
        "type": chart_type,
        "title": title,
        "subtitle": subtitle,
        "footnote": footnote,
        "x": {"label": x_label, "categories": [_clean(c) for c in (categories or [])]},
        "y": {"label": y_label, "format": y_format},
        "series": series_list or [],
        "annotations": annotations or [],
        "highlight": highlight or [],
        "stacked": stacked,
        "options": options or {},
    }


def threshold(value: float, label: str, tone: str = "warn") -> dict:
    """خط آستانه روی نمودار."""
    return {"type": "threshold", "value": _clean(value), "label": label, "tone": tone}


def column(key: str, label: str, fmt: str = "number", *, bar: bool = False, tone_key: str | None = None) -> dict:
    """تعریف یک ستون جدول. bar=True یک میله درون‌سلولی متناسب با مقدار می‌کشد."""
    out = {"key": key, "label": label, "format": fmt}
    if bar:
        out["bar"] = True
    if tone_key:
        out["toneKey"] = tone_key
    return out


def table(title: str, columns: list[dict], rows: list[dict], *, subtitle: str = "", footnote: str = "") -> dict:
    return {
        "title": title,
        "subtitle": subtitle,
        "footnote": footnote,
        "columns": columns,
        "rows": [{k: _clean(v) for k, v in row.items()} for row in rows],
    }


def filter_spec(key: str, label: str, options: list[str], *, all_label: str = "همه") -> dict:
    """یک فیلتر کشویی در نوار بالای صفحه سؤال."""
    return {
        "key": key,
        "label": label,
        "allLabel": all_label,
        "options": [{"value": o, "label": o} for o in options],
    }


def tab_spec(key: str, label: str, options: list[dict]) -> dict:
    """گروه تب برای جابه‌جایی بین برش‌های مختلف یک تحلیل."""
    return {"key": key, "label": label, "options": options}


def response(
    qid: str,
    *,
    kpis: list[dict] | None = None,
    insights: list[dict] | None = None,
    charts: list[dict] | None = None,
    tables: list[dict] | None = None,
    filters: list[dict] | None = None,
    tabs: list[dict] | None = None,
    footnote: str = "",
    extra: dict | None = None,
) -> dict:
    payload = {
        "id": qid,
        "kpis": kpis or [],
        "insights": insights or [],
        "charts": charts or [],
        "tables": tables or [],
        "filters": filters or [],
        "tabs": tabs or [],
        "footnote": footnote,
    }
    if extra:
        payload.update(_clean(extra))
    return payload
