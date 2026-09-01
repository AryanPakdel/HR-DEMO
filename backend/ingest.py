"""خواندن فایل اکسل، اعتبارسنجی ساختار و ساخت ستون‌های مشتق."""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

from .schema import (
    CATEGORICAL_COLUMNS,
    NUMERIC_COLUMNS,
    PERSIAN_MONTHS,
    REQUIRED_COLUMNS,
    SchemaError,
    validate_columns,
)


def read_excel(content: bytes) -> pd.DataFrame:
    """بایت‌های فایل اکسل را به DataFrame تمیز و آماده تحلیل تبدیل می‌کند."""
    try:
        raw = pd.read_excel(io.BytesIO(content), sheet_name=0, engine="openpyxl")
    except SchemaError:
        raise
    except Exception as exc:  # فایل خراب، فرمت غیراکسل، یا شیت غیرقابل خواندن
        raise SchemaError(
            "فایل قابل خواندن نیست.",
            detail=f"خواندن فایل اکسل با خطا مواجه شد: {exc}",
        ) from exc

    raw.columns = [str(c).strip() for c in raw.columns]
    validate_columns(raw.columns)

    df = raw[REQUIRED_COLUMNS].copy()

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in CATEGORICAL_COLUMNS:
        df[col] = df[col].astype("string").str.strip()

    # ردیف‌هایی که کلید زمانی یا ابعاد اصلی ندارند قابل تحلیل نیستند
    df = df.dropna(subset=["month_index", "department", "job_level", "channel"])
    if df.empty:
        raise SchemaError(
            "فایل هیچ ردیف داده معتبری ندارد.",
            detail="پس از حذف ردیف‌های ناقص، هیچ رکوردی باقی نماند.",
        )

    df = df.reset_index(drop=True)
    return _derive(df)


def _derive(df: pd.DataFrame) -> pd.DataFrame:
    """ستون‌های محاسباتی که چند تحلیل به آنها نیاز دارند."""
    df["month_index"] = df["month_index"].astype(int)
    df["year_no"] = df["year_no"].astype(int)

    month_pos = {name: i for i, name in enumerate(PERSIAN_MONTHS)}
    df["month_no"] = df["month"].map(month_pos).astype("Int64")
    # اگر نام ماه ناشناخته بود، از month_index بازسازی می‌شود
    df["month_no"] = df["month_no"].fillna(pd.Series(df["month_index"] % 12)).astype(int)
    df["season"] = (df["month_no"] // 3).astype(int)
    df["quarter_index"] = (df["month_index"] // 3).astype(int)

    # سهم زمانی که نه در HR و نه در انتظار تأیید مدیر سپری شده است
    df["other_days"] = (
        df["time_to_fill"] - df["hr_processing_days"] - df["manager_approval_days"]
    ).clip(lower=0)

    # تعداد پست‌های همزمان باز در همان واحد و همان ماه — ویژگی مدل پیش‌بینی
    df["concurrent_openings"] = df.groupby(
        ["month_index", "department"], observed=True
    )["id"].transform("size").astype(int)

    df["hired"] = df["hired"].fillna(0).astype(int)
    df["offer_accepted"] = df["offer_accepted"].fillna(0).astype(int)

    return df


def summarize(df: pd.DataFrame) -> dict:
    """خلاصه‌ای از مجموعه داده برای نمایش پس از بارگذاری."""
    hires = int(df["hired"].sum())
    total = int(len(df))
    months = int(df["month_index"].nunique())
    return {
        "rows": total,
        "hires": hires,
        "months": months,
        "years": int(df["year_no"].nunique()),
        "departments": int(df["department"].nunique()),
        "channels": int(df["channel"].nunique()),
        "recruiters": int(df["recruiter"].nunique()),
        "acceptance_rate": round(hires / total, 4) if total else 0.0,
        "avg_time_to_fill": round(float(df["time_to_fill"].mean()), 1),
        "total_cost": float(df["total_cost"].sum()),
        "cost_per_hire": float(df["total_cost"].sum() / hires) if hires else 0.0,
        "period_label": _period_label(df),
    }


def _period_label(df: pd.DataFrame) -> str:
    first = df.loc[df["month_index"].idxmin()]
    last = df.loc[df["month_index"].idxmax()]
    return f"سال {first['year_no']} · {first['month']} تا سال {last['year_no']} · {last['month']}"


def dimension_options(df: pd.DataFrame, column: str, order: list[str] | None = None) -> list[str]:
    """مقادیر یکتای یک بعد، در صورت وجود با ترتیب معنادار."""
    values = [v for v in df[column].dropna().unique().tolist()]
    if order:
        ranked = [v for v in order if v in values]
        return ranked + sorted(v for v in values if v not in order)
    return sorted(values)


def month_axis(df: pd.DataFrame) -> list[dict]:
    """محور زمانی کامل: هر ماه با برچسب «سال ۱ · مهر»."""
    seen = (
        df[["month_index", "year_no", "month"]]
        .drop_duplicates(subset=["month_index"])
        .sort_values("month_index")
    )
    out = []
    for _, row in seen.iterrows():
        out.append(
            {
                "index": int(row["month_index"]),
                "year": int(row["year_no"]),
                "month": str(row["month"]),
                "label": f"سال {int(row['year_no'])} · {row['month']}",
                "short": str(row["month"]),
            }
        )
    return out


def safe_div(numerator, denominator, default=0.0):
    """تقسیم امن که در صورت صفر بودن مخرج مقدار پیش‌فرض می‌دهد."""
    denominator = float(denominator)
    if denominator == 0 or np.isnan(denominator):
        return default
    value = float(numerator) / denominator
    return default if np.isnan(value) else value
