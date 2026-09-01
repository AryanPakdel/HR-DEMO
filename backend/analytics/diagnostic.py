"""تحلیل‌های سطح تشخیصی: پنج سؤال «چرا این اتفاق افتاده است؟»"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .. import viz
from ..ingest import dimension_options, safe_div
from ..schema import DIMENSIONS, EDUCATION_ORDER, FUNNEL_STAGES, JOB_LEVEL_ORDER
from .common import (
    PALETTE,
    apply_filters,
    correlation,
    funnel_totals,
    group_stats,
    minmax,
    num,
    order_categories,
    outlier_threshold,
    pct,
    rate_by,
    relative,
    zscore,
)

SLICE_TABS = [
    {"value": "department", "label": "واحد سازمانی"},
    {"value": "job_level", "label": "سطح شغلی"},
    {"value": "channel", "label": "کانال جذب"},
    {"value": "recruiter", "label": "کارشناس جذب"},
]


def _filters(df: pd.DataFrame, keys=("department", "job_level", "channel")) -> list[dict]:
    specs = []
    for key in keys:
        order = JOB_LEVEL_ORDER if key == "job_level" else (EDUCATION_ORDER if key == "education" else None)
        specs.append(viz.filter_spec(key, DIMENSIONS[key], dimension_options(df, key, order)))
    years = sorted(df["year_no"].unique().tolist())
    specs.append(viz.filter_spec("year", "سال", [str(int(y)) for y in years], all_label="همه سال‌ها"))
    return specs


def _pick(params: dict, key: str, allowed: list[str], default: str) -> str:
    value = params.get(key)
    return value if value in allowed else default


# ═══════════════════════════ G1 ═══════════════════════════
def g1_time_to_fill_root_cause(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    if len(data) < 3:
        return viz.response("g1", insights=[viz.insight("داده کافی برای این تحلیل وجود ندارد.", "warn")])

    dimension = _pick(params, "slice", [t["value"] for t in SLICE_TABS], "department")
    dim_label = DIMENSIONS[dimension]

    mean, std, threshold_value = outlier_threshold(data, "time_to_fill", sigmas=1.0)
    stats = group_stats(data, dimension, "time_to_fill")
    stats["is_outlier"] = stats["mean"] > threshold_value

    labels = stats["group"].tolist()
    outlier_idx = [i for i, flag in enumerate(stats["is_outlier"].tolist()) if flag]

    outlier_chart = viz.chart(
        "hbar",
        f"میانگین زمان پر شدن پست به تفکیک {dim_label}",
        labels,
        [viz.series("میانگین روز", stats["mean"], PALETTE[0])],
        subtitle=f"گروه‌هایی که از آستانه {num(threshold_value)} روز عبور کرده‌اند نقطه تمرکز علامت خورده‌اند",
        y_label="روز",
        annotations=[
            viz.threshold(mean, f"میانگین کل {num(mean)} روز", "info"),
            viz.threshold(threshold_value, f"آستانه پرت {num(threshold_value)} روز", "warn"),
        ],
        highlight=outlier_idx,
    )

    # تجزیه زمان به بازه‌های مسئولیت
    delay = (
        data.groupby(dimension, observed=True)[["hr_processing_days", "manager_approval_days", "other_days", "time_to_fill"]]
        .mean()
        .reset_index()
        .rename(columns={dimension: "group"})
        .sort_values("time_to_fill", ascending=False)
        .reset_index(drop=True)
    )
    delay_labels = delay["group"].tolist()
    delay_chart = viz.chart(
        "bar",
        f"تفکیک زمان بین ذی‌نفعان فرآیند — {dim_label}",
        delay_labels,
        [
            viz.series("پردازش منابع انسانی", delay["hr_processing_days"], PALETTE[2]),
            viz.series("تأیید مدیر واحد", delay["manager_approval_days"], PALETTE[3]),
            viz.series("سایر مراحل", delay["other_days"], PALETTE[4]),
        ],
        subtitle="میانگین تعداد روز سپری‌شده در هر بازه مسئولیت",
        y_label="روز",
        stacked=True,
    )

    rows = []
    for _, r in stats.iterrows():
        subset = data[data[dimension] == r["group"]]
        hr_days = float(subset["hr_processing_days"].mean())
        mgr_days = float(subset["manager_approval_days"].mean())
        rows.append(
            {
                "group": r["group"],
                "mean": float(r["mean"]),
                "vs_avg": float(r["mean"] - mean),
                "vs_avg_pct": safe_div(r["mean"] - mean, mean),
                "std": float(r["std"]),
                "count": int(r["count"]),
                "hr_days": hr_days,
                "mgr_days": mgr_days,
                "hr_share": safe_div(hr_days, r["mean"]),
                "status": "نقطه تمرکز" if r["is_outlier"] else "در محدوده عادی",
                "tone": "bad" if r["is_outlier"] else "good",
            }
        )

    hr_corr = correlation(data["hr_processing_days"], data["time_to_fill"])
    mgr_corr = correlation(data["manager_approval_days"], data["time_to_fill"])
    hr_total = float(data["hr_processing_days"].mean())
    mgr_total = float(data["manager_approval_days"].mean())

    insights = []
    if outlier_idx:
        names = "، ".join(f"«{labels[i]}»" for i in outlier_idx)
        worst = stats.iloc[outlier_idx[0]]
        insights.append(
            viz.insight(
                f"{len(outlier_idx)} گروه از آستانه {num(threshold_value)} روز (میانگین کل + یک انحراف معیار) عبور کرده‌اند: {names}. "
                f"کندترین آنها با {num(worst['mean'])} روز، {relative(worst['mean'], mean)} از میانگین سازمان است.",
                "bad",
                "گروه‌های پرت",
            )
        )
    else:
        insights.append(
            viz.insight(
                f"هیچ گروهی از آستانه {num(threshold_value)} روز عبور نکرده است؛ پراکندگی زمان پر شدن در این برش کنترل‌شده است.",
                "good",
                "بدون نقطه پرت",
            )
        )

    culprit = "منابع انسانی" if hr_corr > mgr_corr else "مدیر واحد درخواست‌کننده"
    insights.append(
        viz.insight(
            f"همبستگی زمان پردازش منابع انسانی با کل زمان پر شدن {num(hr_corr, 2)} و همبستگی تأیید مدیر واحد "
            f"{num(mgr_corr, 2)} است. به‌طور میانگین {num(hr_total)} روز در منابع انسانی و {num(mgr_total)} روز "
            f"در انتظار تأیید مدیر سپری می‌شود — منشأ اصلی کندی سمت {culprit} است.",
            "warn",
            "منشأ تأخیر",
        )
    )

    if rows:
        heaviest = max(rows, key=lambda r: r["hr_share"])
        lightest = min(rows, key=lambda r: r["hr_share"])
        insights.append(
            viz.insight(
                f"سهم مرحله منابع انسانی از کل زمان در «{heaviest['group']}» به {pct(heaviest['hr_share'])} می‌رسد "
                f"({num(heaviest['hr_days'])} روز) در حالی که در «{lightest['group']}» تنها {pct(lightest['hr_share'])} است "
                f"({num(lightest['hr_days'])} روز). این شکاف نشان می‌دهد کندی از فرآیند داخلی می‌آید نه از دشواری ذاتی پست.",
                "warn",
                "تمرکز اقدام اصلاحی",
            )
        )

    return viz.response(
        "g1",
        kpis=[
            viz.kpi("میانگین کل", mean, "days"),
            viz.kpi("انحراف معیار", std, "days", "پراکندگی زمان پر شدن"),
            viz.kpi("آستانه نقطه تمرکز", threshold_value, "days", "میانگین + یک انحراف معیار", "warn"),
            viz.kpi("گروه‌های پرت", len(outlier_idx), "number", f"از {len(labels)} گروه", "bad" if outlier_idx else "good"),
        ],
        insights=insights,
        charts=[outlier_chart, delay_chart],
        tables=[
            viz.table(
                f"جدول ریشه‌یابی به تفکیک {dim_label}",
                [
                    viz.column("group", dim_label, "text"),
                    viz.column("mean", "میانگین زمان", "days", bar=True),
                    viz.column("vs_avg", "اختلاف با میانگین", "delta_days"),
                    viz.column("vs_avg_pct", "اختلاف نسبی", "delta_percent"),
                    viz.column("hr_days", "روز در منابع انسانی", "days"),
                    viz.column("mgr_days", "روز تأیید مدیر", "days"),
                    viz.column("hr_share", "سهم منابع انسانی", "percent"),
                    viz.column("count", "تعداد پست", "number"),
                    viz.column("status", "وضعیت", "badge", tone_key="tone"),
                ],
                rows,
                footnote="آستانه پرت طبق منطق فایل تحلیل: میانگین کل به علاوه یک انحراف معیار.",
            )
        ],
        filters=_filters(df),
        tabs=[viz.tab_spec("slice", "برش بر اساس", SLICE_TABS)],
    )


# ═══════════════════════════ G2 ═══════════════════════════
def g2_funnel_bottleneck(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    if data.empty:
        return viz.response("g2", insights=[viz.insight("با فیلترهای انتخاب‌شده رکوردی یافت نشد.", "warn")])

    dimension = _pick(params, "slice", [t["value"] for t in SLICE_TABS], "department")
    dim_label = DIMENSIONS[dimension]

    stages = funnel_totals(data)
    transitions = stages[1:]  # مرحله اول ورودی است و نرخ عبور ندارد
    worst = min(transitions, key=lambda s: s["step_rate"]) if transitions else None
    worst_pos = stages.index(worst) if worst else 0

    funnel_chart = viz.chart(
        "funnel",
        "قیف استخدام با درصد افت هر مرحله",
        [s["label"] for s in stages],
        [viz.series("تعداد", [s["value"] for s in stages])],
        subtitle="مرحله با کمترین نرخ عبور، گلوگاه اصلی است",
        y_label="نفر",
        highlight=[worst_pos] if worst else [],
        options={
            "stepRates": [s["step_rate"] for s in stages],
            "overallRates": [s["overall_rate"] for s in stages],
        },
    )

    # هیت‌مپ نرخ تبدیل: مرحله × گروه
    groups = order_categories(dimension, sorted(data[dimension].dropna().unique().tolist()))
    stage_names = [label for _, label in FUNNEL_STAGES[1:]]
    matrix = []
    group_worst = []
    for group in groups:
        subset = data[data[dimension] == group]
        gstages = funnel_totals(subset)
        rates = [s["step_rate"] if s["step_rate"] is not None else 0.0 for s in gstages[1:]]
        matrix.append(rates)
        if rates:
            worst_i = int(np.argmin(rates))
            group_worst.append(
                {
                    "group": group,
                    "stage": stage_names[worst_i],
                    "rate": rates[worst_i],
                    "applicants": int(subset["applicants"].sum()),
                    "accepted": int(subset["accepted"].sum()),
                    "overall": safe_div(subset["accepted"].sum(), subset["applicants"].sum()),
                }
            )

    heatmap = viz.chart(
        "heatmap",
        f"نرخ عبور هر مرحله به تفکیک {dim_label}",
        stage_names,
        [viz.series(groups[i], matrix[i]) for i in range(len(groups))],
        subtitle="رنگ روشن‌تر یعنی نرخ عبور بالاتر؛ خانه‌های تیره گلوگاه هستند",
        y_label="نرخ عبور",
        y_format="percent",
        options={"rows": groups},
    )

    stage_rows = [
        {
            "stage": s["label"],
            "value": int(s["value"]),
            "step_rate": s["step_rate"],
            "drop_count": None if s["step_rate"] is None else int(stages[i - 1]["value"] - s["value"]),
            "drop_rate": s["drop_rate"],
            "overall_rate": s["overall_rate"],
            "status": "گلوگاه اصلی" if s is worst else "",
            "tone": "bad" if s is worst else "neutral",
        }
        for i, s in enumerate(stages)
    ]

    group_worst = sorted(group_worst, key=lambda r: r["rate"])

    insights = []
    if worst:
        lost = stages[worst_pos - 1]["value"] - worst["value"]
        insights.append(
            viz.insight(
                f"گلوگاه اصلی قیف، گذار به مرحله «{worst['label']}» است: تنها {pct(worst['step_rate'])} از "
                f"کاندیداهای مرحله قبل عبور می‌کنند و {num(lost, 0)} نفر در همین نقطه حذف می‌شوند.",
                "bad",
                "گلوگاه اصلی",
            )
        )
    if group_worst:
        tight = group_worst[0]
        insights.append(
            viz.insight(
                f"سخت‌گیرانه‌ترین ترکیب، مرحله «{tight['stage']}» در «{tight['group']}» با نرخ عبور {pct(tight['rate'])} است. "
                f"نرخ تبدیل کلی این گروه از داوطلب تا استخدام {pct(tight['overall'])} است.",
                "warn",
                f"الگو در سطح {dim_label}",
            )
        )
        spread = group_worst[-1]["rate"] - group_worst[0]["rate"]
        if spread > 0.05:
            insights.append(
                viz.insight(
                    f"گلوگاه در همه گروه‌ها یکسان نیست؛ فاصله بین سخت‌گیرانه‌ترین و آسان‌ترین گروه "
                    f"{num(spread * 100, 0)} واحد درصد است. یک اقدام اصلاحی واحد برای همه واحدها پاسخ نمی‌دهد.",
                    "info",
                    "تفاوت الگوها",
                )
            )

    return viz.response(
        "g2",
        kpis=[
            viz.kpi("گلوگاه اصلی", worst["label"] if worst else "—", "text", "کمترین نرخ عبور", "bad"),
            viz.kpi("نرخ عبور گلوگاه", worst["step_rate"] if worst else 0, "percent", tone="bad"),
            viz.kpi("نرخ تبدیل کلی قیف", stages[-1]["overall_rate"], "percent", "داوطلب تا استخدام نهایی"),
            viz.kpi("کل داوطلبان", int(stages[0]["value"]), "number"),
        ],
        insights=insights,
        charts=[funnel_chart, heatmap],
        tables=[
            viz.table(
                "نرخ تبدیل و افت هر مرحله",
                [
                    viz.column("stage", "مرحله", "text"),
                    viz.column("value", "تعداد", "number", bar=True),
                    viz.column("drop_count", "تعداد حذف‌شده", "number"),
                    viz.column("step_rate", "نرخ عبور", "percent"),
                    viz.column("drop_rate", "نرخ افت", "percent"),
                    viz.column("overall_rate", "نسبت به ورودی", "percent"),
                    viz.column("status", "وضعیت", "badge", tone_key="tone"),
                ],
                stage_rows,
            ),
            viz.table(
                f"رتبه‌بندی گلوگاه به تفکیک {dim_label}",
                [
                    viz.column("group", dim_label, "text"),
                    viz.column("stage", "تنگ‌ترین مرحله", "text"),
                    viz.column("rate", "نرخ عبور آن مرحله", "percent", bar=True),
                    viz.column("applicants", "داوطلب", "number"),
                    viz.column("accepted", "استخدام", "number"),
                    viz.column("overall", "تبدیل کلی", "percent"),
                ],
                group_worst,
                footnote="مرتب‌شده از تنگ‌ترین گلوگاه به بازترین.",
            ),
        ],
        filters=_filters(df),
        tabs=[viz.tab_spec("slice", "برش بر اساس", SLICE_TABS)],
    )


# ═══════════════════════════ G3 ═══════════════════════════
# پنج شاخص سنجش کانال: (کلید، برچسب، آیا بیشتر بهتر است، وزن پیش‌فرض درصدی)
QUALITY_METRICS = [
    ("conversion", "نرخ تبدیل داوطلب به استخدام", True, 20),
    ("cost_per_hire", "سرانه هزینه هر استخدام", False, 20),
    ("first_year_turnover", "نرخ خروج سال اول", False, 25),
    ("performance_6m", "عملکرد ۶ ماهه", True, 20),
    ("satisfaction", "رضایت کارجو", True, 15),
]


def _channel_metrics(data: pd.DataFrame) -> pd.DataFrame:
    hired = data[data["hired"] == 1]
    grouped = (
        data.groupby("channel", observed=True)
        .agg(
            applicants=("applicants", "sum"),
            requisitions=("id", "size"),
            hires=("hired", "sum"),
            cost=("total_cost", "sum"),
        )
        .reset_index()
        .rename(columns={"channel": "group"})
    )
    quality = (
        hired.groupby("channel", observed=True)
        .agg(
            first_year_turnover=("first_year_turnover", "mean"),
            performance_6m=("performance_score_6m", "mean"),
            satisfaction=("applicant_satisfaction", "mean"),
        )
        .reset_index()
        .rename(columns={"channel": "group"})
    )
    merged = grouped.merge(quality, on="group", how="left")
    merged["conversion"] = merged.apply(lambda r: safe_div(r["hires"], r["applicants"]), axis=1)
    merged["cost_per_hire"] = merged.apply(lambda r: safe_div(r["cost"], r["hires"]), axis=1)
    for col in ("first_year_turnover", "performance_6m", "satisfaction"):
        merged[col] = merged[col].fillna(merged[col].mean())
    return merged


def g3_channel_quality(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    metrics = _channel_metrics(data)
    if len(metrics) < 2:
        return viz.response("g3", insights=[viz.insight("برای مقایسه کانال‌ها حداقل دو کانال لازم است.", "warn")])

    # وزن‌های قابل تنظیم توسط کاربر، نرمال‌شده به مجموع ۱
    weights = {}
    for key, _, _, default in QUALITY_METRICS:
        try:
            weights[key] = max(0.0, float(params.get(f"w_{key}", default)))
        except (TypeError, ValueError):
            weights[key] = float(default)
    total_weight = sum(weights.values()) or 1.0
    weights = {k: v / total_weight for k, v in weights.items()}

    score = pd.Series(np.zeros(len(metrics)), index=metrics.index)
    for key, _, higher_better, _ in QUALITY_METRICS:
        normalized = minmax(metrics[key], higher_is_better=higher_better)
        metrics[f"n_{key}"] = normalized
        score += normalized * weights[key]
    metrics["score"] = score
    metrics = metrics.sort_values("score", ascending=False).reset_index(drop=True)

    # شاخص کیفیت خالص (بدون هزینه) برای محور عمودی نمودار پراکندگی
    qual_keys = [k for k, _, _, _ in QUALITY_METRICS if k != "cost_per_hire"]
    metrics["quality_index"] = metrics[[f"n_{k}" for k in qual_keys]].mean(axis=1)

    scatter = viz.chart(
        "scatter",
        "کیفیت در برابر حجم کانال جذب",
        [],
        [
            viz.series(
                r["group"],
                [
                    {
                        "x": float(r["applicants"]),
                        "y": float(r["quality_index"]),
                        "r": float(r["cost_per_hire"]),
                        "label": r["group"],
                    }
                ],
                PALETTE[i % len(PALETTE)],
            )
            for i, r in metrics.iterrows()
        ],
        subtitle="محور افقی حجم داوطلب، محور عمودی شاخص کیفیت و اندازه حباب سرانه هزینه است",
        x_label="تعداد داوطلب",
        y_label="شاخص کیفیت (۰ تا ۱)",
        options={"bubbleFormat": "currency", "bubbleLabel": "سرانه هزینه", "xFormat": "number"},
    )

    score_chart = viz.chart(
        "hbar",
        "شاخص ترکیبی کانال‌ها بر پایه وزن‌های انتخابی شما",
        metrics["group"].tolist(),
        [viz.series("شاخص ترکیبی", metrics["score"], PALETTE[0])],
        subtitle="مقدار بین ۰ تا ۱؛ هرچه بالاتر، کانال در مجموع مطلوب‌تر",
        y_label="امتیاز",
        highlight=[0],
        options={"highlightTone": "good"},
    )

    rows = [
        {
            "group": r["group"],
            "applicants": int(r["applicants"]),
            "hires": int(r["hires"]),
            "conversion": float(r["conversion"]),
            "cost_per_hire": float(r["cost_per_hire"]),
            "first_year_turnover": float(r["first_year_turnover"]),
            "performance_6m": float(r["performance_6m"]),
            "satisfaction": float(r["satisfaction"]),
            "score": float(r["score"]),
            "rank": i + 1,
        }
        for i, r in metrics.iterrows()
    ]

    best = rows[0]
    worst = rows[-1]
    biggest = max(rows, key=lambda r: r["applicants"])
    cheapest = min(rows, key=lambda r: r["cost_per_hire"])

    insights = [
        viz.insight(
            f"با وزن‌های فعلی، «{best['group']}» با شاخص {num(best['score'], 2)} در صدر و «{worst['group']}» "
            f"با {num(worst['score'], 2)} در قعر رتبه‌بندی قرار دارد.",
            "good",
            "رتبه‌بندی ترکیبی",
        ),
        viz.insight(
            f"«{biggest['group']}» بیشترین حجم ({num(biggest['applicants'], 0)} داوطلب) را می‌آورد اما نرخ خروج سال اول آن "
            f"{pct(biggest['first_year_turnover'])} و عملکرد ۶ ماهه {num(biggest['performance_6m'])} است؛ "
            f"{'حجم بالا اینجا با کیفیت پایین همراه است' if biggest['group'] != best['group'] else 'این کانال هم حجم و هم کیفیت را تأمین می‌کند'}.",
            "warn" if biggest["group"] != best["group"] else "good",
            "حجم در برابر کیفیت",
        ),
        viz.insight(
            f"ارزان‌ترین کانال «{cheapest['group']}» با سرانه {num(cheapest['cost_per_hire'], 0)} است، اما گران‌بودن یک کانال "
            f"لزوماً بد نیست: اگر نرخ خروج سال اول پایین‌تر باشد، هزینه استخدام مجدد صرفه‌جویی می‌شود. "
            f"با اسلایدرهای بالا وزن هر معیار را متناسب با اولویت سازمان خود تنظیم کنید.",
            "info",
            "چگونه تفسیر کنیم",
        ),
    ]

    return viz.response(
        "g3",
        kpis=[
            viz.kpi("بهترین کانال", best["group"], "text", f"شاخص ترکیبی {num(best['score'], 2)}", "good"),
            viz.kpi("ضعیف‌ترین کانال", worst["group"], "text", f"شاخص ترکیبی {num(worst['score'], 2)}", "bad"),
            viz.kpi("پرحجم‌ترین کانال", biggest["group"], "text", f"{num(biggest['applicants'], 0)} داوطلب"),
            viz.kpi("ارزان‌ترین کانال", cheapest["cost_per_hire"], "currency", cheapest["group"], "good"),
        ],
        insights=insights,
        charts=[scatter, score_chart],
        tables=[
            viz.table(
                "کارنامه تفصیلی کانال‌ها",
                [
                    viz.column("rank", "رتبه", "number"),
                    viz.column("group", "کانال جذب", "text"),
                    viz.column("applicants", "داوطلب", "number"),
                    viz.column("hires", "استخدام", "number"),
                    viz.column("conversion", "نرخ تبدیل", "percent"),
                    viz.column("cost_per_hire", "سرانه هزینه", "currency"),
                    viz.column("first_year_turnover", "خروج سال اول", "percent"),
                    viz.column("performance_6m", "عملکرد ۶ ماهه", "number"),
                    viz.column("satisfaction", "رضایت کارجو", "score"),
                    viz.column("score", "شاخص ترکیبی", "number", bar=True),
                ],
                rows,
            )
        ],
        filters=_filters(df, keys=("department", "job_level")),
        extra={
            "weights": {
                "title": "وزن‌دهی معیارها",
                "description": "مجموع وزن‌ها به‌طور خودکار نرمال می‌شود؛ نسبت بین آنهاست که اهمیت دارد.",
                "items": [
                    {
                        "key": key,
                        "label": label,
                        "higherIsBetter": higher,
                        "value": round(weights[key] * 100),
                        "default": default,
                    }
                    for key, label, higher, default in QUALITY_METRICS
                ],
            }
        },
    )


# ═══════════════════════════ G4 ═══════════════════════════
COHORT_NUMERIC = [
    ("years_experience", "سابقه کاری (سال)", "number"),
    ("interview_score", "نمره مصاحبه", "number"),
    ("technical_test_score", "نمره آزمون فنی", "number"),
    ("applicant_satisfaction", "رضایت از فرآیند جذب", "score"),
    ("time_to_fill", "طول فرآیند جذب (روز)", "days"),
    ("hr_processing_days", "روزهای پردازش منابع انسانی", "days"),
    ("salary_gap", "شکاف حقوق با بازار", "percent"),
    ("performance_score_6m", "عملکرد ۶ ماهه", "number"),
]

COHORT_CATEGORICAL = [
    ("channel", "کانال جذب"),
    ("department", "واحد سازمانی"),
    ("job_level", "سطح شغلی"),
    ("recruiter", "کارشناس جذب"),
]


def g4_early_attrition(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    tracked = data[(data["hired"] == 1) & data["first_year_turnover"].notna()]
    stayed = tracked[tracked["first_year_turnover"] == 0]
    left = tracked[tracked["first_year_turnover"] == 1]

    if len(left) < 3 or len(stayed) < 3:
        return viz.response(
            "g4",
            insights=[viz.insight("برای مقایسه دو کوهورت، داده کافی در هر دو گروه وجود ندارد.", "warn")],
            filters=_filters(df),
        )

    dimension = _pick(params, "slice", [t["value"] for t in SLICE_TABS], "channel")
    dim_label = DIMENSIONS[dimension]
    overall_rate = float(tracked["first_year_turnover"].mean())

    diffs = []
    for key, label, fmt in COHORT_NUMERIC:
        a, b = stayed[key].dropna(), left[key].dropna()
        if len(a) < 3 or len(b) < 3:
            continue
        mean_stay, mean_left = float(a.mean()), float(b.mean())
        base = abs(mean_stay) if mean_stay != 0 else 1.0
        diffs.append(
            {
                "factor": label,
                "stayed": mean_stay,
                "left": mean_left,
                "diff": mean_left - mean_stay,
                "diff_pct": (mean_left - mean_stay) / base,
                "format": fmt,
                "magnitude": abs((mean_left - mean_stay) / base),
            }
        )
    diffs.sort(key=lambda d: d["magnitude"], reverse=True)

    diff_chart = viz.chart(
        "diffbar",
        "اختلاف نسبی عوامل بین دو کوهورت",
        [d["factor"] for d in diffs],
        [viz.series("اختلاف نسبی گروه ترک‌کرده نسبت به ماندگار", [d["diff_pct"] for d in diffs], PALETTE[0])],
        subtitle="مقادیر مثبت یعنی آن عامل در گروه ترک‌کرده بالاتر بوده است",
        y_label="اختلاف نسبی",
        y_format="percent",
    )

    cat_rate = rate_by(tracked, dimension, "first_year_turnover")
    cat_chart = viz.chart(
        "bar",
        f"نرخ خروج سال اول به تفکیک {dim_label}",
        cat_rate["group"].tolist(),
        [viz.series("نرخ خروج سال اول", cat_rate["rate"], PALETTE[2])],
        subtitle="مقایسه با میانگین کل سازمان",
        y_label="نرخ",
        y_format="percent",
        annotations=[viz.threshold(overall_rate, f"میانگین کل {pct(overall_rate)}", "info")],
        highlight=[0],
    )

    # قوی‌ترین عامل دسته‌ای: بیشترین دامنه نرخ خروج بین سطوح آن بعد
    cat_rows = []
    for key, label in COHORT_CATEGORICAL:
        rates = rate_by(tracked, key, "first_year_turnover")
        if len(rates) < 2:
            continue
        top, bottom = rates.iloc[0], rates.iloc[-1]
        cat_rows.append(
            {
                "factor": label,
                "worst": f"{top['group']} ({pct(top['rate'])})",
                "best": f"{bottom['group']} ({pct(bottom['rate'])})",
                "spread": float(top["rate"] - bottom["rate"]),
                "ratio": safe_div(top["rate"], bottom["rate"]),
            }
        )
    cat_rows.sort(key=lambda r: r["spread"], reverse=True)

    cohort_rows = [
        {
            "factor": d["factor"],
            "stayed": d["stayed"],
            "left": d["left"],
            "diff": d["diff"],
            "diff_pct": d["diff_pct"],
            "format": d["format"],
        }
        for d in diffs
    ]

    insights = [
        viz.insight(
            f"از {num(len(tracked), 0)} استخدام رهگیری‌شده، {num(len(left), 0)} نفر ({pct(overall_rate)}) در سال اول "
            f"سازمان را ترک کرده‌اند و {num(len(stayed), 0)} نفر مانده‌اند.",
            "info",
            "دو کوهورت",
        )
    ]
    if cat_rows:
        strongest = cat_rows[0]
        insights.append(
            viz.insight(
                f"قوی‌ترین تمایزدهنده در میان عوامل دسته‌ای، «{strongest['factor']}» است: از {strongest['best']} "
                f"تا {strongest['worst']} — یعنی {num(strongest['ratio'], 1)} برابر اختلاف. "
                f"این عامل بیش از ویژگی‌های فردی کاندیدا با ترک خدمت زودهنگام مرتبط است.",
                "bad",
                "مؤثرترین عامل",
            )
        )
    if diffs:
        top_num = diffs[0]
        direction = "بالاتر" if top_num["diff"] > 0 else "پایین‌تر"
        insights.append(
            viz.insight(
                f"در میان متغیرهای عددی، «{top_num['factor']}» بیشترین اختلاف را دارد: گروه ترک‌کرده "
                f"{num(abs(top_num['diff_pct']) * 100, 0)}٪ {direction} از گروه ماندگار "
                f"({num(top_num['left'], 2)} در برابر {num(top_num['stayed'], 2)}).",
                "warn",
                "مؤثرترین متغیر عددی",
            )
        )
    insights.append(
        viz.insight(
            "این تحلیل همبستگی را نشان می‌دهد نه علیت؛ برای تأیید رابطه علّی باید اثر عوامل هم‌زمان "
            "(مثلاً واحد سازمانی و کانال جذب که با هم مرتبط‌اند) کنترل شود.",
            "info",
            "محدودیت تفسیر",
        )
    )

    return viz.response(
        "g4",
        kpis=[
            viz.kpi("نرخ خروج سال اول", overall_rate, "percent", tone="warn"),
            viz.kpi("گروه ماندگار", int(len(stayed)), "number", tone="good"),
            viz.kpi("گروه ترک‌کرده", int(len(left)), "number", tone="bad"),
            viz.kpi(
                "بدترین گروه",
                float(cat_rate.iloc[0]["rate"]),
                "percent",
                f"{dim_label}: {cat_rate.iloc[0]['group']}",
                "bad",
            ),
        ],
        insights=insights,
        charts=[cat_chart, diff_chart],
        tables=[
            viz.table(
                "مقایسه دو کوهورت در متغیرهای عددی",
                [
                    viz.column("factor", "عامل", "text"),
                    viz.column("stayed", "گروه ماندگار", "dynamic"),
                    viz.column("left", "گروه ترک‌کرده", "dynamic"),
                    viz.column("diff", "اختلاف مطلق", "dynamic"),
                    viz.column("diff_pct", "اختلاف نسبی", "delta_percent", bar=True),
                ],
                cohort_rows,
                subtitle="مرتب‌شده بر شدت اختلاف",
            ),
            viz.table(
                "قدرت تمایز عوامل دسته‌ای",
                [
                    viz.column("factor", "عامل", "text"),
                    viz.column("worst", "بیشترین نرخ خروج", "text"),
                    viz.column("best", "کمترین نرخ خروج", "text"),
                    viz.column("spread", "دامنه اختلاف", "percent", bar=True),
                    viz.column("ratio", "نسبت بیشترین به کمترین", "number"),
                ],
                cat_rows,
            ),
        ],
        filters=_filters(df),
        tabs=[viz.tab_spec("slice", "برش بر اساس", SLICE_TABS)],
    )


# ═══════════════════════════ G5 ═══════════════════════════
# شاخص‌های کارنامه: (کلید، برچسب، آیا بیشتر بهتر است، قالب)
RECRUITER_METRICS = [
    ("time_to_fill", "زمان پر شدن پست", False, "days"),
    ("cost_per_hire", "سرانه هزینه هر استخدام", False, "currency"),
    ("offer_rate", "نرخ پذیرش پیشنهاد", True, "percent"),
    ("satisfaction", "رضایت کارجو", True, "score"),
    ("retention", "ماندگاری سال اول", True, "percent"),
]


def g5_recruiter_scorecard(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    if data["recruiter"].nunique() < 2:
        return viz.response("g5", insights=[viz.insight("برای مقایسه، حداقل دو کارشناس جذب لازم است.", "warn")])

    hired = data[data["hired"] == 1]
    base = (
        data.groupby("recruiter", observed=True)
        .agg(
            requisitions=("id", "size"),
            hires=("hired", "sum"),
            cost=("total_cost", "sum"),
            time_to_fill=("time_to_fill", "mean"),
            offer_rate=("offer_accepted", "mean"),
        )
        .reset_index()
        .rename(columns={"recruiter": "group"})
    )
    quality = (
        hired.groupby("recruiter", observed=True)
        .agg(satisfaction=("applicant_satisfaction", "mean"), turnover=("first_year_turnover", "mean"))
        .reset_index()
        .rename(columns={"recruiter": "group"})
    )
    m = base.merge(quality, on="group", how="left")
    m["cost_per_hire"] = m.apply(lambda r: safe_div(r["cost"], r["hires"]), axis=1)
    m["satisfaction"] = m["satisfaction"].fillna(m["satisfaction"].mean())
    m["turnover"] = m["turnover"].fillna(m["turnover"].mean())
    m["retention"] = 1 - m["turnover"]

    for key, _, higher, _ in RECRUITER_METRICS:
        m[f"z_{key}"] = zscore(m[key], higher_is_better=higher)
        m[f"n_{key}"] = minmax(m[key], higher_is_better=higher)
    m["score"] = m[[f"z_{k}" for k, _, _, _ in RECRUITER_METRICS]].mean(axis=1)
    m = m.sort_values("score", ascending=False).reset_index(drop=True)

    names = m["group"].tolist()
    metric_labels = [label for _, label, _, _ in RECRUITER_METRICS]

    radar = viz.chart(
        "radar",
        "مقایسه چندبعدی کارشناسان جذب",
        metric_labels,
        [
            viz.series(
                r["group"],
                [float(r[f"n_{key}"]) for key, _, _, _ in RECRUITER_METRICS],
                PALETTE[i % len(PALETTE)],
            )
            for i, r in m.iterrows()
        ],
        subtitle="همه شاخص‌ها به بازه ۰ تا ۱ نرمال شده‌اند و در همه محورها «بیرونی‌تر بهتر» است",
        y_label="امتیاز نرمال‌شده",
    )

    score_chart = viz.chart(
        "hbar",
        "امتیاز کل کارنامه (میانگین Z-score پنج شاخص)",
        names,
        [viz.series("امتیاز کل", m["score"], PALETTE[0])],
        subtitle="مقدار صفر یعنی دقیقاً در حد میانگین سازمان",
        y_label="Z-score",
        annotations=[viz.threshold(0, "میانگین سازمان", "info")],
        highlight=[0],
        options={"highlightTone": "good"},
    )

    rows = [
        {
            "rank": i + 1,
            "group": r["group"],
            "requisitions": int(r["requisitions"]),
            "hires": int(r["hires"]),
            "time_to_fill": float(r["time_to_fill"]),
            "cost_per_hire": float(r["cost_per_hire"]),
            "offer_rate": float(r["offer_rate"]),
            "satisfaction": float(r["satisfaction"]),
            "retention": float(r["retention"]),
            "score": float(r["score"]),
        }
        for i, r in m.iterrows()
    ]

    best, worst = rows[0], rows[-1]
    ttf_gap = worst["time_to_fill"] - best["time_to_fill"]

    strengths = []
    for key, label, higher, _ in RECRUITER_METRICS:
        leader = m.loc[m[f"z_{key}"].idxmax()]
        strengths.append(f"{label}: {leader['group']}")

    insights = [
        viz.insight(
            f"«{best['group']}» با امتیاز کل {num(best['score'], 2)} در صدر کارنامه است و «{worst['group']}» "
            f"با {num(worst['score'], 2)} در انتها. امتیاز صفر معادل عملکرد میانگین سازمان است.",
            "good",
            "رتبه‌بندی کلی",
        ),
        viz.insight(
            f"فاصله زمان پر شدن پست بین بهترین و ضعیف‌ترین کارنامه {num(abs(ttf_gap))} روز است "
            f"({num(best['time_to_fill'])} در برابر {num(worst['time_to_fill'])} روز). "
            "پیش از نتیجه‌گیری باید بررسی شود که ترکیب پست‌های واگذارشده به هر کارشناس مشابه است یا نه.",
            "warn",
            "شکاف عملکرد",
        ),
        viz.insight(
            "پیشتاز هر شاخص — " + " · ".join(strengths),
            "info",
            "نقاط قوت تفکیکی",
        ),
    ]

    return viz.response(
        "g5",
        kpis=[
            viz.kpi("بهترین کارنامه", best["group"], "text", f"امتیاز {num(best['score'], 2)}", "good"),
            viz.kpi("سریع‌ترین زمان پر شدن", min(r["time_to_fill"] for r in rows), "days", tone="good"),
            viz.kpi("بالاترین نرخ پذیرش", max(r["offer_rate"] for r in rows), "percent", tone="good"),
            viz.kpi("تعداد کارشناس", len(rows), "number"),
        ],
        insights=insights,
        charts=[radar, score_chart],
        tables=[
            viz.table(
                "کارنامه تفصیلی کارشناسان جذب",
                [
                    viz.column("rank", "رتبه", "number"),
                    viz.column("group", "کارشناس جذب", "text"),
                    viz.column("requisitions", "تقاضای واگذارشده", "number"),
                    viz.column("hires", "استخدام نهایی", "number"),
                    viz.column("time_to_fill", "زمان پر شدن", "days"),
                    viz.column("cost_per_hire", "سرانه هزینه", "currency"),
                    viz.column("offer_rate", "نرخ پذیرش پیشنهاد", "percent"),
                    viz.column("satisfaction", "رضایت کارجو", "score"),
                    viz.column("retention", "ماندگاری سال اول", "percent"),
                    viz.column("score", "امتیاز کل", "number", bar=True),
                ],
                rows,
                footnote="نرمال‌سازی با Z-score انجام شده تا کارشناسانی با حجم و نوع پست متفاوت منصفانه مقایسه شوند.",
            )
        ],
        filters=_filters(df, keys=("department", "job_level", "channel")),
    )


HANDLERS = {
    "g1": g1_time_to_fill_root_cause,
    "g2": g2_funnel_bottleneck,
    "g3": g3_channel_quality,
    "g4": g4_early_attrition,
    "g5": g5_recruiter_scorecard,
}
