"""ابزارهای مشترک تحلیل: گروه‌بندی، قیف، تشخیص پرت، نرمال‌سازی و همبستگی."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..schema import (
    EDUCATION_ORDER,
    FUNNEL_STAGES,
    JOB_LEVEL_ORDER,
    PERSIAN_MONTHS,
)

# پالت کیفی هماهنگ با توکن‌های فرانت‌اند
PALETTE = ["#2DD4BF", "#818CF8", "#F472B6", "#FBBF24", "#38BDF8", "#A3E635"]
TONE_GOOD = "#34D399"
TONE_WARN = "#FBBF24"
TONE_BAD = "#F87171"

DIMENSION_ORDER = {
    "job_level": JOB_LEVEL_ORDER,
    "education": EDUCATION_ORDER,
    "month": PERSIAN_MONTHS,
}


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """فیلترهای ابعادی و سال را روی داده اعمال می‌کند."""
    out = df
    for key in ("department", "job_level", "channel", "recruiter", "education"):
        value = filters.get(key)
        if value and value != "__all__":
            out = out[out[key] == value]
    year = filters.get("year")
    if year and year != "__all__":
        try:
            out = out[out["year_no"] == int(year)]
        except (TypeError, ValueError):
            pass
    return out


def order_categories(dimension: str, values: list[str]) -> list[str]:
    """ترتیب معنادار برای ابعادی که ترتیب طبیعی دارند."""
    preferred = DIMENSION_ORDER.get(dimension)
    if not preferred:
        return values
    ranked = [v for v in preferred if v in values]
    return ranked + [v for v in values if v not in preferred]


def group_stats(df: pd.DataFrame, dimension: str, value_col: str) -> pd.DataFrame:
    """میانگین، انحراف معیار، میانه و تعداد هر گروه، مرتب‌شده نزولی بر میانگین."""
    grouped = (
        df.groupby(dimension, observed=True)[value_col]
        .agg(mean="mean", std="std", median="median", count="size", min="min", max="max")
        .reset_index()
        .rename(columns={dimension: "group"})
    )
    grouped["std"] = grouped["std"].fillna(0.0)
    return grouped.sort_values("mean", ascending=False).reset_index(drop=True)


def outlier_threshold(df: pd.DataFrame, value_col: str, sigmas: float = 1.0) -> tuple[float, float, float]:
    """آستانه پرت طبق منطق فایل تحلیل: میانگین کل + n انحراف معیار."""
    mean = float(df[value_col].mean())
    std = float(df[value_col].std(ddof=0))
    return mean, std, mean + sigmas * std


def rate_by(df: pd.DataFrame, dimension: str, flag_col: str) -> pd.DataFrame:
    """نرخ یک متغیر دودویی به تفکیک یک بعد، همراه با تعداد پایه."""
    sub = df[df[flag_col].notna()]
    grouped = (
        sub.groupby(dimension, observed=True)[flag_col]
        .agg(rate="mean", count="size", events="sum")
        .reset_index()
        .rename(columns={dimension: "group"})
    )
    return grouped.sort_values("rate", ascending=False).reset_index(drop=True)


def funnel_totals(df: pd.DataFrame) -> list[dict]:
    """مجموع هر مرحله قیف با نرخ تبدیل نسبت به مرحله قبل و نسبت به ورودی."""
    stages = []
    previous = None
    first = float(df[FUNNEL_STAGES[0][0]].sum()) if len(df) else 0.0
    for key, label in FUNNEL_STAGES:
        total = float(df[key].sum()) if len(df) else 0.0
        step = (total / previous) if previous else 1.0
        stages.append(
            {
                "key": key,
                "label": label,
                "value": total,
                "step_rate": step if previous else None,
                "drop_rate": (1 - step) if previous else None,
                "overall_rate": (total / first) if first else 0.0,
            }
        )
        previous = total
    return stages


def zscore(values: pd.Series, *, higher_is_better: bool = True) -> pd.Series:
    """نرمال‌سازی Z-score با جهت‌دهی معنایی (شاخص‌های کمتر-بهتر معکوس می‌شوند)."""
    std = float(values.std(ddof=0))
    if std == 0 or np.isnan(std):
        return pd.Series(np.zeros(len(values)), index=values.index)
    z = (values - float(values.mean())) / std
    return z if higher_is_better else -z


def minmax(values: pd.Series, *, higher_is_better: bool = True) -> pd.Series:
    """نرمال‌سازی به بازه ۰ تا ۱ با جهت‌دهی معنایی."""
    lo, hi = float(values.min()), float(values.max())
    if hi == lo:
        return pd.Series(np.full(len(values), 0.5), index=values.index)
    scaled = (values - lo) / (hi - lo)
    return scaled if higher_is_better else 1 - scaled


def correlation(x: pd.Series, y: pd.Series) -> float:
    """همبستگی پیرسون با حذف مقادیر خالی."""
    frame = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(frame) < 3 or frame["x"].std(ddof=0) == 0 or frame["y"].std(ddof=0) == 0:
        return 0.0
    return float(frame["x"].corr(frame["y"]))


def histogram(values: pd.Series, bins: int = 12) -> tuple[list[str], list[int], list[float]]:
    """هیستوگرام با برچسب بازه‌ها. خروجی: (برچسب‌ها، فراوانی، مرکز بازه‌ها)"""
    clean = values.dropna()
    if clean.empty:
        return [], [], []
    counts, edges = np.histogram(clean, bins=bins)
    labels = [f"{edges[i]:.0f}–{edges[i + 1]:.0f}" for i in range(len(counts))]
    centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(counts))]
    return labels, [int(c) for c in counts], centers


def pct(value: float) -> str:
    """درصد با یک رقم اعشار برای متن‌های تحلیلی."""
    return f"{value * 100:.1f}٪"


def num(value: float, digits: int = 1) -> str:
    """عدد با تعداد رقم اعشار مشخص برای متن‌های تحلیلی."""
    return f"{value:,.{digits}f}"


def relative(value: float, baseline: float) -> str:
    """اختلاف نسبی یک مقدار با مبنا، به صورت متن («۲۹٪ بالاتر»)."""
    if baseline == 0:
        return "—"
    diff = (value - baseline) / abs(baseline)
    direction = "بالاتر" if diff >= 0 else "پایین‌تر"
    return f"{abs(diff) * 100:.0f}٪ {direction}"


def monthly_series(df: pd.DataFrame, agg: dict, granularity: str = "month") -> pd.DataFrame:
    """سری زمانی تجمیع‌شده در سطح ماه، فصل یا سال."""
    if granularity == "year":
        key, label_cols = "year_no", ["year_no"]
    elif granularity == "quarter":
        key, label_cols = "quarter_index", ["quarter_index", "year_no"]
    else:
        key, label_cols = "month_index", ["month_index", "year_no", "month"]

    grouped = df.groupby(key, observed=True).agg(**agg).reset_index()
    # label_cols همیشه شامل خود key است؛ dict.fromkeys ترتیب را حفظ و تکرار را حذف می‌کند
    meta_cols = list(dict.fromkeys(label_cols))
    meta = df[meta_cols].drop_duplicates(subset=[key]).sort_values(key)
    merged = grouped.merge(meta, on=key, how="left", suffixes=("", "_meta"))
    merged = merged.sort_values(key).reset_index(drop=True)

    if granularity == "year":
        merged["label"] = merged["year_no"].apply(lambda y: f"سال {int(y)}")
    elif granularity == "quarter":
        merged["label"] = merged.apply(
            lambda r: f"سال {int(r['year_no'])} · فصل {int(r['quarter_index']) % 4 + 1}", axis=1
        )
    else:
        merged["label"] = merged.apply(
            lambda r: f"سال {int(r['year_no'])} · {r['month']}", axis=1
        )
    return merged


GRANULARITY_TABS = [
    {"value": "month", "label": "ماهانه"},
    {"value": "quarter", "label": "فصلی"},
    {"value": "year", "label": "سالانه"},
]
