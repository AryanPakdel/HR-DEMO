"""تحلیل‌های سطح توصیفی: هشت سؤال «چه اتفاقی افتاده است؟»"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .. import viz
from ..ingest import dimension_options, safe_div
from ..schema import DIMENSIONS, EDUCATION_ORDER, FUNNEL_STAGES, JOB_LEVEL_ORDER
from .common import (
    GRANULARITY_TABS,
    PALETTE,
    apply_filters,
    correlation,
    funnel_totals,
    group_stats,
    histogram,
    monthly_series,
    num,
    order_categories,
    pct,
    rate_by,
    relative,
)

# ابعادی که کاربر می‌تواند تحلیل را بر اساس آنها برش بزند
SLICE_TABS = [
    {"value": "department", "label": "واحد سازمانی"},
    {"value": "job_level", "label": "سطح شغلی"},
    {"value": "channel", "label": "کانال جذب"},
    {"value": "recruiter", "label": "کارشناس جذب"},
]


def _base_filters(df: pd.DataFrame, keys=("department", "job_level", "channel")) -> list[dict]:
    """فیلترهای استاندارد بالای صفحه سؤال."""
    specs = []
    for key in keys:
        order = JOB_LEVEL_ORDER if key == "job_level" else (EDUCATION_ORDER if key == "education" else None)
        specs.append(viz.filter_spec(key, DIMENSIONS[key], dimension_options(df, key, order)))
    years = sorted(df["year_no"].unique().tolist())
    specs.append(
        viz.filter_spec("year", "سال", [str(int(y)) for y in years], all_label="همه سال‌ها")
    )
    return specs


def _pick(params: dict, key: str, allowed: list[str], default: str) -> str:
    value = params.get(key)
    return value if value in allowed else default


# ═══════════════════════════ D1 ═══════════════════════════
def d1_demand_trend(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    if data.empty:
        return viz.response("d1", insights=[viz.insight("با فیلترهای انتخاب‌شده رکوردی یافت نشد.", "warn")])

    granularity = _pick(params, "granularity", ["month", "quarter", "year"], "month")

    total_req = int(len(data))
    total_hires = int(data["hired"].sum())
    exits = int(data["first_year_turnover"].fillna(0).sum())
    net = total_hires - exits

    ts = monthly_series(
        data,
        {
            "requisitions": ("id", "size"),
            "hires": ("hired", "sum"),
            "exits": ("first_year_turnover", "sum"),
        },
        granularity,
    )
    ts["exits"] = ts["exits"].fillna(0)
    ts["net_cumulative"] = (ts["hires"] - ts["exits"]).cumsum()

    labels = ts["label"].tolist()

    trend_chart = viz.chart(
        "line",
        "روند تقاضای جذب و استخدام نهایی",
        labels,
        [
            viz.series("تقاضای جذب", ts["requisitions"], PALETTE[0]),
            viz.series("استخدام نهایی", ts["hires"], PALETTE[1]),
            viz.series("خروج سال اول", ts["exits"], PALETTE[2]),
        ],
        subtitle="تعداد رکورد در هر بازه زمانی",
        y_label="تعداد",
    )

    net_chart = viz.chart(
        "area",
        "نیروی خالص افزوده‌شده (تجمعی)",
        labels,
        [viz.series("خالص تجمعی", ts["net_cumulative"], PALETTE[0])],
        subtitle="استخدام نهایی منهای خروج سال اول، به‌صورت انباشته",
        y_label="نفر",
    )

    yearly = (
        data.groupby("year_no", observed=True)
        .agg(
            requisitions=("id", "size"),
            hires=("hired", "sum"),
            exits=("first_year_turnover", "sum"),
            avg_ttf=("time_to_fill", "mean"),
        )
        .reset_index()
        .sort_values("year_no")
    )
    yearly["exits"] = yearly["exits"].fillna(0)
    rows = [
        {
            "year": f"سال {int(r['year_no'])}",
            "requisitions": int(r["requisitions"]),
            "hires": int(r["hires"]),
            "fill_rate": safe_div(r["hires"], r["requisitions"]),
            "exits": int(r["exits"]),
            "net": int(r["hires"] - r["exits"]),
            "avg_ttf": float(r["avg_ttf"]),
        }
        for _, r in yearly.iterrows()
    ]

    insights = []
    if len(yearly) >= 2:
        first, last = yearly.iloc[0], yearly.iloc[-1]
        insights.append(
            viz.insight(
                f"تقاضای جذب از {num(first['requisitions'], 0)} مورد در سال {int(first['year_no'])} به "
                f"{num(last['requisitions'], 0)} مورد در سال {int(last['year_no'])} رسیده است — "
                f"{relative(last['requisitions'], first['requisitions'])}.",
                "good" if last["requisitions"] >= first["requisitions"] else "warn",
                "روند تقاضا",
            )
        )
    peak = ts.loc[ts["requisitions"].idxmax()]
    low = ts.loc[ts["requisitions"].idxmin()]
    insights.append(
        viz.insight(
            f"بیشترین حجم تقاضا در «{peak['label']}» با {num(peak['requisitions'], 0)} مورد و "
            f"کمترین آن در «{low['label']}» با {num(low['requisitions'], 0)} مورد ثبت شده است.",
            "info",
            "اوج و کف",
        )
    )
    insights.append(
        viz.insight(
            f"از {num(total_req, 0)} تقاضای ثبت‌شده، {num(total_hires, 0)} مورد ({pct(safe_div(total_hires, total_req))}) "
            f"به استخدام نهایی رسیده و پس از کسر {num(exits, 0)} خروج سال اول، "
            f"{num(net, 0)} نفر خالص به سازمان افزوده شده است.",
            "info",
            "جمع‌بندی دوره",
        )
    )

    return viz.response(
        "d1",
        kpis=[
            viz.kpi("کل تقاضای جذب", total_req, "number", "تعداد درخواست ثبت‌شده در دوره"),
            viz.kpi("استخدام نهایی", total_hires, "number", "تقاضاهایی که به پذیرش رسیدند"),
            viz.kpi("نرخ تکمیل تقاضا", safe_div(total_hires, total_req), "percent", "استخدام نهایی تقسیم بر کل تقاضا", "good"),
            viz.kpi("نیروی خالص افزوده", net, "number", "استخدام نهایی منهای خروج سال اول"),
        ],
        insights=insights,
        charts=[trend_chart, net_chart],
        tables=[
            viz.table(
                "خلاصه سالانه",
                [
                    viz.column("year", "سال", "text"),
                    viz.column("requisitions", "تقاضای جذب", "number", bar=True),
                    viz.column("hires", "استخدام نهایی", "number"),
                    viz.column("fill_rate", "نرخ تکمیل", "percent"),
                    viz.column("exits", "خروج سال اول", "number"),
                    viz.column("net", "خالص افزوده", "number"),
                    viz.column("avg_ttf", "میانگین زمان پر شدن", "days"),
                ],
                rows,
            )
        ],
        filters=_base_filters(df),
        tabs=[viz.tab_spec("granularity", "بازه زمانی", GRANULARITY_TABS)],
    )


# ═══════════════════════════ D2 ═══════════════════════════
def d2_composition(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    if data.empty:
        return viz.response("d2", insights=[viz.insight("با فیلترهای انتخاب‌شده رکوردی یافت نشد.", "warn")])

    total = len(data)

    dept = (
        data.groupby("department", observed=True)
        .agg(requisitions=("id", "size"), hires=("hired", "sum"))
        .reset_index()
        .sort_values("requisitions", ascending=False)
    )
    dept_chart = viz.chart(
        "bar",
        "تقاضا و استخدام به تفکیک واحد سازمانی",
        dept["department"].tolist(),
        [
            viz.series("تقاضای جذب", dept["requisitions"], PALETTE[0]),
            viz.series("استخدام نهایی", dept["hires"], PALETTE[1]),
        ],
        subtitle=f"مجموع {num(total, 0)} تقاضا در دوره",
        y_label="تعداد",
    )

    levels = order_categories("job_level", data["job_level"].dropna().unique().tolist())
    level_counts = data["job_level"].value_counts().reindex(levels).fillna(0)
    level_chart = viz.chart(
        "donut",
        "توزیع سطح شغلی",
        levels,
        [viz.series("تقاضا", level_counts.tolist())],
        subtitle="سهم هر سطح شغلی از کل تقاضا",
        y_label="تعداد",
    )

    edus = order_categories("education", data["education"].dropna().unique().tolist())
    edu_counts = data["education"].value_counts().reindex(edus).fillna(0)
    edu_chart = viz.chart(
        "donut",
        "توزیع مدرک تحصیلی",
        edus,
        [viz.series("تقاضا", edu_counts.tolist())],
        subtitle="سهم هر مدرک از کل تقاضا",
        y_label="تعداد",
    )

    cross = (
        data.pivot_table(index="department", columns="job_level", values="id", aggfunc="size", observed=True)
        .reindex(columns=levels)
        .fillna(0)
    )
    cross_chart = viz.chart(
        "bar",
        "تقاطع واحد سازمانی و سطح شغلی",
        cross.index.tolist(),
        [viz.series(lv, cross[lv].tolist(), PALETTE[i % len(PALETTE)]) for i, lv in enumerate(levels)],
        subtitle="تعداد تقاضا در هر ترکیب",
        y_label="تعداد",
        stacked=True,
    )

    rows = []
    for _, r in dept.iterrows():
        rows.append(
            {
                "department": r["department"],
                "requisitions": int(r["requisitions"]),
                "share": safe_div(r["requisitions"], total),
                "hires": int(r["hires"]),
                "fill_rate": safe_div(r["hires"], r["requisitions"]),
            }
        )

    top = dept.iloc[0]
    best_fill = max(rows, key=lambda r: r["fill_rate"])
    worst_fill = min(rows, key=lambda r: r["fill_rate"])

    insights = [
        viz.insight(
            f"واحد «{top['department']}» با {num(top['requisitions'], 0)} تقاضا "
            f"({pct(safe_div(top['requisitions'], total))} از کل) بیشترین حجم جذب را دارد.",
            "info",
            "بیشترین حجم",
        ),
        viz.insight(
            f"بالاترین نرخ تکمیل تقاضا در «{best_fill['department']}» با {pct(best_fill['fill_rate'])} و "
            f"پایین‌ترین در «{worst_fill['department']}» با {pct(worst_fill['fill_rate'])} است — "
            f"فاصله {num((best_fill['fill_rate'] - worst_fill['fill_rate']) * 100, 1)} واحد درصد.",
            "warn" if best_fill["fill_rate"] - worst_fill["fill_rate"] > 0.1 else "info",
            "شکاف نرخ تکمیل",
        ),
    ]
    if levels:
        dominant = level_counts.idxmax()
        insights.append(
            viz.insight(
                f"{pct(safe_div(level_counts.max(), total))} از تقاضاها مربوط به سطح «{dominant}» است؛ "
                f"ترکیب مدرک تحصیلی نیز با {pct(safe_div(edu_counts.max(), total))} در «{edu_counts.idxmax()}» تمرکز دارد.",
                "info",
                "ترکیب غالب",
            )
        )

    return viz.response(
        "d2",
        kpis=[
            viz.kpi("کل تقاضا", total, "number"),
            viz.kpi("تعداد واحد سازمانی", int(data["department"].nunique()), "number"),
            viz.kpi("تعداد سطح شغلی", int(data["job_level"].nunique()), "number"),
            viz.kpi("سهم مدرک غالب", safe_div(edu_counts.max(), total), "percent", f"مدرک {edu_counts.idxmax()}"),
        ],
        insights=insights,
        charts=[dept_chart, cross_chart, level_chart, edu_chart],
        tables=[
            viz.table(
                "جزئیات واحدهای سازمانی",
                [
                    viz.column("department", "واحد سازمانی", "text"),
                    viz.column("requisitions", "تقاضا", "number", bar=True),
                    viz.column("share", "سهم از کل", "percent"),
                    viz.column("hires", "استخدام نهایی", "number"),
                    viz.column("fill_rate", "نرخ تکمیل", "percent"),
                ],
                rows,
            )
        ],
        filters=_base_filters(df, keys=("department", "job_level", "education")),
    )


# ═══════════════════════════ D3 ═══════════════════════════
def d3_time_to_fill(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    if data.empty:
        return viz.response("d3", insights=[viz.insight("با فیلترهای انتخاب‌شده رکوردی یافت نشد.", "warn")])

    dimension = _pick(params, "slice", [t["value"] for t in SLICE_TABS], "department")
    ttf = data["time_to_fill"].dropna()

    mean, median = float(ttf.mean()), float(ttf.median())
    p90 = float(ttf.quantile(0.9))

    labels, counts, _ = histogram(ttf, bins=14)
    hist_chart = viz.chart(
        "histogram",
        "توزیع زمان پر شدن پست",
        labels,
        [viz.series("تعداد پست", counts, PALETTE[0])],
        subtitle="فراوانی پست‌ها در هر بازه روز",
        y_label="تعداد پست",
        x_label="روز",
        annotations=[viz.threshold(mean, f"میانگین {num(mean)} روز", "info")],
    )

    stats = group_stats(data, dimension, "time_to_fill")
    stats_labels = stats["group"].tolist()
    if dimension in ("job_level", "education"):
        ordered = order_categories(dimension, stats_labels)
        stats = stats.set_index("group").reindex(ordered).reset_index()
        stats_labels = stats["group"].tolist()

    dim_label = DIMENSIONS[dimension]
    slice_chart = viz.chart(
        "hbar",
        f"میانگین زمان پر شدن به تفکیک {dim_label}",
        stats_labels,
        [viz.series("میانگین روز", stats["mean"], PALETTE[0])],
        subtitle="خط عمودی میانگین کل سازمان را نشان می‌دهد",
        y_label="روز",
        annotations=[viz.threshold(mean, f"میانگین کل {num(mean)} روز", "info")],
    )

    ts = monthly_series(data, {"avg_ttf": ("time_to_fill", "mean")}, "month")
    trend_chart = viz.chart(
        "line",
        "روند ماهانه زمان پر شدن پست",
        ts["label"].tolist(),
        [viz.series("میانگین روز", ts["avg_ttf"], PALETTE[0])],
        subtitle="میانگین در هر ماه",
        y_label="روز",
        annotations=[viz.threshold(mean, f"میانگین دوره {num(mean)} روز", "info")],
    )

    rows = [
        {
            "group": r["group"],
            "mean": float(r["mean"]),
            "median": float(r["median"]),
            "std": float(r["std"]),
            "min": float(r["min"]),
            "max": float(r["max"]),
            "count": int(r["count"]),
            "vs_avg": float(r["mean"] - mean),
        }
        for _, r in stats.iterrows()
    ]

    slowest, fastest = stats.iloc[0], stats.iloc[-1]
    hr_corr = correlation(data["hr_processing_days"], data["time_to_fill"])

    insights = [
        viz.insight(
            f"میانگین زمان پر شدن یک پست {num(mean)} روز و میانه {num(median)} روز است؛ "
            f"۱۰٪ کندترین پست‌ها بیش از {num(p90)} روز طول می‌کشند.",
            "info",
            "تصویر کلی",
        ),
        viz.insight(
            f"کندترین گروه «{slowest['group']}» با {num(slowest['mean'])} روز است و سریع‌ترین «{fastest['group']}» "
            f"با {num(fastest['mean'])} روز — اختلاف {num(slowest['mean'] - fastest['mean'])} روز "
            f"({relative(slowest['mean'], fastest['mean'])}).",
            "warn" if slowest["mean"] - fastest["mean"] > 8 else "info",
            f"شکاف در {dim_label}",
        ),
        viz.insight(
            f"همبستگی روزهای پردازش منابع انسانی با کل زمان پر شدن {num(hr_corr, 2)} است؛ "
            f"به‌طور میانگین {pct(safe_div(data['hr_processing_days'].mean(), mean))} از کل زمان در این مرحله سپری می‌شود.",
            "warn" if hr_corr > 0.4 else "info",
            "سهم مرحله منابع انسانی",
        ),
    ]

    return viz.response(
        "d3",
        kpis=[
            viz.kpi("میانگین زمان پر شدن", mean, "days", "میانگین کل پست‌های دوره"),
            viz.kpi("میانه", median, "days", "نصف پست‌ها زیر این مقدار پر شده‌اند"),
            viz.kpi("سریع‌ترین پست", float(ttf.min()), "days", tone="good"),
            viz.kpi("کندترین پست", float(ttf.max()), "days", tone="warn"),
        ],
        insights=insights,
        charts=[hist_chart, slice_chart, trend_chart],
        tables=[
            viz.table(
                f"آمار تفصیلی به تفکیک {dim_label}",
                [
                    viz.column("group", dim_label, "text"),
                    viz.column("mean", "میانگین", "days", bar=True),
                    viz.column("median", "میانه", "days"),
                    viz.column("std", "انحراف معیار", "days"),
                    viz.column("min", "کمینه", "days"),
                    viz.column("max", "بیشینه", "days"),
                    viz.column("count", "تعداد پست", "number"),
                    viz.column("vs_avg", "اختلاف با میانگین کل", "delta_days"),
                ],
                rows,
            )
        ],
        filters=_base_filters(df),
        tabs=[viz.tab_spec("slice", "برش بر اساس", SLICE_TABS)],
    )


# ═══════════════════════════ D4 ═══════════════════════════
def d4_funnel(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    if data.empty:
        return viz.response("d4", insights=[viz.insight("با فیلترهای انتخاب‌شده رکوردی یافت نشد.", "warn")])

    dimension = _pick(params, "slice", [t["value"] for t in SLICE_TABS], "department")
    stages = funnel_totals(data)

    funnel_chart = viz.chart(
        "funnel",
        "قیف استخدام",
        [s["label"] for s in stages],
        [viz.series("تعداد", [s["value"] for s in stages])],
        subtitle="تعداد افراد در هر مرحله و نرخ عبور از مرحله قبل",
        y_label="نفر",
        options={
            "stepRates": [s["step_rate"] for s in stages],
            "overallRates": [s["overall_rate"] for s in stages],
        },
    )

    applicants = float(data["applicants"].sum())
    accepted = float(data["accepted"].sum())
    openings = int(len(data))
    selection_rate = safe_div(accepted, applicants)
    per_opening = safe_div(applicants, openings)

    grouped = (
        data.groupby(dimension, observed=True)
        .agg(applicants=("applicants", "sum"), openings=("id", "size"), accepted=("accepted", "sum"))
        .reset_index()
        .rename(columns={dimension: "group"})
    )
    grouped["per_opening"] = grouped.apply(lambda r: safe_div(r["applicants"], r["openings"]), axis=1)
    grouped["selection"] = grouped.apply(lambda r: safe_div(r["accepted"], r["applicants"]), axis=1)
    grouped = grouped.sort_values("per_opening", ascending=False).reset_index(drop=True)

    dim_label = DIMENSIONS[dimension]
    per_opening_chart = viz.chart(
        "bar",
        f"میانگین داوطلب به ازای هر پست — {dim_label}",
        grouped["group"].tolist(),
        [viz.series("داوطلب به ازای پست", grouped["per_opening"], PALETTE[0])],
        subtitle="کل داوطلبان تقسیم بر تعداد پست",
        y_label="نفر",
        annotations=[viz.threshold(per_opening, f"میانگین کل {num(per_opening)}", "info")],
    )

    selection_chart = viz.chart(
        "bar",
        f"نرخ انتخاب نهایی — {dim_label}",
        grouped["group"].tolist(),
        [viz.series("نرخ انتخاب", grouped["selection"], PALETTE[1])],
        subtitle="پذیرفته‌شدگان تقسیم بر کل داوطلبان",
        y_label="نرخ",
        y_format="percent",
        annotations=[viz.threshold(selection_rate, f"میانگین کل {pct(selection_rate)}", "info")],
    )

    stage_rows = [
        {
            "stage": s["label"],
            "value": int(s["value"]),
            "step_rate": s["step_rate"],
            "drop_rate": s["drop_rate"],
            "overall_rate": s["overall_rate"],
        }
        for s in stages
    ]

    drops = [s for s in stages if s["drop_rate"] is not None]
    worst = max(drops, key=lambda s: s["drop_rate"]) if drops else None
    worst_index = stages.index(worst) if worst else 0

    insights = [
        viz.insight(
            f"از {num(applicants, 0)} داوطلب، {num(accepted, 0)} نفر به استخدام رسیده‌اند؛ "
            f"نرخ انتخاب نهایی {pct(selection_rate)} است — یعنی از هر "
            f"{num(safe_div(applicants, accepted), 0)} داوطلب، یک نفر استخدام می‌شود.",
            "info",
            "نرخ انتخاب",
        )
    ]
    if worst:
        insights.append(
            viz.insight(
                f"بیشترین افت در گذار به مرحله «{worst['label']}» رخ می‌دهد: "
                f"{pct(worst['drop_rate'])} از کاندیداهای مرحله قبل حذف می‌شوند.",
                "warn",
                "بزرگ‌ترین افت",
            )
        )
    insights.append(
        viz.insight(
            f"هر پست به‌طور میانگین {num(per_opening)} داوطلب جذب می‌کند؛ بیشترین جذابیت در "
            f"«{grouped.iloc[0]['group']}» با {num(grouped.iloc[0]['per_opening'])} داوطلب و کمترین در "
            f"«{grouped.iloc[-1]['group']}» با {num(grouped.iloc[-1]['per_opening'])} داوطلب.",
            "info",
            "جذابیت پست‌ها",
        )
    )

    return viz.response(
        "d4",
        kpis=[
            viz.kpi("کل داوطلبان", applicants, "number"),
            viz.kpi("نرخ انتخاب نهایی", selection_rate, "percent", "پذیرفته‌شده تقسیم بر کل داوطلب"),
            viz.kpi("داوطلب به ازای هر پست", per_opening, "number", f"روی {num(openings, 0)} پست"),
            viz.kpi("نرخ پذیرش پیشنهاد", safe_div(accepted, float(data["offered"].sum())), "percent", "پذیرش تقسیم بر پیشنهاد"),
        ],
        insights=insights,
        charts=[funnel_chart, per_opening_chart, selection_chart],
        tables=[
            viz.table(
                "نرخ تبدیل مرحله‌به‌مرحله",
                [
                    viz.column("stage", "مرحله", "text"),
                    viz.column("value", "تعداد", "number", bar=True),
                    viz.column("step_rate", "نرخ عبور از مرحله قبل", "percent"),
                    viz.column("drop_rate", "افت", "percent"),
                    viz.column("overall_rate", "نسبت به ورودی قیف", "percent"),
                ],
                stage_rows,
                footnote="مرحله اول مبنای محاسبه است و نرخ عبور برای آن تعریف نمی‌شود.",
            ),
            viz.table(
                f"مقایسه به تفکیک {dim_label}",
                [
                    viz.column("group", dim_label, "text"),
                    viz.column("openings", "تعداد پست", "number"),
                    viz.column("applicants", "داوطلب", "number"),
                    viz.column("per_opening", "داوطلب به ازای پست", "number", bar=True),
                    viz.column("accepted", "پذیرش نهایی", "number"),
                    viz.column("selection", "نرخ انتخاب", "percent"),
                ],
                grouped.to_dict("records"),
            ),
        ],
        filters=_base_filters(df),
        tabs=[viz.tab_spec("slice", "برش بر اساس", SLICE_TABS)],
        extra={"worstStageIndex": worst_index},
    )


# ═══════════════════════════ D5 ═══════════════════════════
def d5_cost_per_hire(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    if data.empty:
        return viz.response("d5", insights=[viz.insight("با فیلترهای انتخاب‌شده رکوردی یافت نشد.", "warn")])

    total_cost = float(data["total_cost"].sum())
    hires = int(data["hired"].sum())
    cph = safe_div(total_cost, hires)

    def cost_table(dimension: str) -> pd.DataFrame:
        grouped = (
            data.groupby(dimension, observed=True)
            .agg(cost=("total_cost", "sum"), hires=("hired", "sum"), requisitions=("id", "size"))
            .reset_index()
            .rename(columns={dimension: "group"})
        )
        grouped["cph"] = grouped.apply(lambda r: safe_div(r["cost"], r["hires"]), axis=1)
        return grouped.sort_values("cph", ascending=False).reset_index(drop=True)

    by_level = cost_table("job_level")
    ordered = order_categories("job_level", by_level["group"].tolist())
    by_level = by_level.set_index("group").reindex(ordered).reset_index()
    by_dept = cost_table("department")

    level_chart = viz.chart(
        "bar",
        "سرانه هزینه هر استخدام به تفکیک سطح شغلی",
        by_level["group"].tolist(),
        [viz.series("سرانه هزینه", by_level["cph"], PALETTE[0])],
        subtitle="کل هزینه گروه تقسیم بر تعداد استخدام نهایی همان گروه",
        y_label="هزینه",
        y_format="currency",
        annotations=[viz.threshold(cph, f"سرانه کل سازمان", "info")],
    )

    dept_chart = viz.chart(
        "hbar",
        "سرانه هزینه هر استخدام به تفکیک واحد سازمانی",
        by_dept["group"].tolist(),
        [viz.series("سرانه هزینه", by_dept["cph"], PALETTE[1])],
        subtitle="مرتب‌شده از گران‌ترین به ارزان‌ترین",
        y_label="هزینه",
        y_format="currency",
        annotations=[viz.threshold(cph, "سرانه کل سازمان", "info")],
    )

    combo = (
        data.groupby(["department", "job_level"], observed=True)
        .agg(cost=("total_cost", "sum"), hires=("hired", "sum"), requisitions=("id", "size"))
        .reset_index()
    )
    combo = combo[combo["hires"] > 0].copy()
    combo["cph"] = combo.apply(lambda r: safe_div(r["cost"], r["hires"]), axis=1)
    combo = combo.sort_values("cph", ascending=False).reset_index(drop=True)
    rows = [
        {
            "combo": f"{r['department']} · {r['job_level']}",
            "requisitions": int(r["requisitions"]),
            "hires": int(r["hires"]),
            "cost": float(r["cost"]),
            "cph": float(r["cph"]),
            "vs_avg": safe_div(r["cph"] - cph, cph),
        }
        for _, r in combo.iterrows()
    ]

    highest, lowest = combo.iloc[0], combo.iloc[-1]
    insights = [
        viz.insight(
            f"سرانه هزینه هر استخدام در کل سازمان {num(cph, 0)} است؛ مجموع هزینه دوره "
            f"{num(total_cost, 0)} برای {num(hires, 0)} استخدام نهایی.",
            "info",
            "سرانه کل",
        ),
        viz.insight(
            f"گران‌ترین ترکیب «{highest['department']} · {highest['job_level']}» با سرانه {num(highest['cph'], 0)} "
            f"است — {relative(highest['cph'], cph)} از میانگین سازمان.",
            "warn",
            "گران‌ترین",
        ),
        viz.insight(
            f"ارزان‌ترین ترکیب «{lowest['department']} · {lowest['job_level']}» با سرانه {num(lowest['cph'], 0)} است؛ "
            f"نسبت گران‌ترین به ارزان‌ترین {num(safe_div(highest['cph'], lowest['cph']), 1)} برابر.",
            "good",
            "ارزان‌ترین",
        ),
    ]

    return viz.response(
        "d5",
        kpis=[
            viz.kpi("سرانه هزینه هر استخدام", cph, "currency", "کل هزینه تقسیم بر استخدام نهایی"),
            viz.kpi("مجموع هزینه دوره", total_cost, "currency"),
            viz.kpi("بالاترین سرانه", float(highest["cph"]), "currency", f"{highest['department']} · {highest['job_level']}", "warn"),
            viz.kpi("پایین‌ترین سرانه", float(lowest["cph"]), "currency", f"{lowest['department']} · {lowest['job_level']}", "good"),
        ],
        insights=insights,
        charts=[level_chart, dept_chart],
        tables=[
            viz.table(
                "رتبه‌بندی سرانه هزینه بر پایه ترکیب واحد و سطح شغلی",
                [
                    viz.column("combo", "واحد · سطح شغلی", "text"),
                    viz.column("requisitions", "تقاضا", "number"),
                    viz.column("hires", "استخدام", "number"),
                    viz.column("cost", "هزینه کل", "currency"),
                    viz.column("cph", "سرانه هر استخدام", "currency", bar=True),
                    viz.column("vs_avg", "اختلاف با میانگین", "delta_percent"),
                ],
                rows,
                footnote="ترکیب‌هایی که هیچ استخدام نهایی نداشته‌اند در این جدول نمی‌آیند چون سرانه برای آنها تعریف نمی‌شود.",
            )
        ],
        filters=_base_filters(df),
    )


# ═══════════════════════════ D6 ═══════════════════════════
COST_PARTS = [
    ("cost_ad", "آگهی"),
    ("cost_agency", "مشاور استخدام"),
    ("cost_referral", "معرفی کارکنان"),
    ("cost_assessment", "ارزیابی و آزمون"),
    ("cost_hr_time", "زمان کارشناس جذب"),
]


def d6_channels(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    if data.empty:
        return viz.response("d6", insights=[viz.insight("با فیلترهای انتخاب‌شده رکوردی یافت نشد.", "warn")])

    grouped = (
        data.groupby("channel", observed=True)
        .agg(
            requisitions=("id", "size"),
            hires=("hired", "sum"),
            applicants=("applicants", "sum"),
            cost=("total_cost", "sum"),
        )
        .reset_index()
        .rename(columns={"channel": "group"})
    )
    grouped["cph"] = grouped.apply(lambda r: safe_div(r["cost"], r["hires"]), axis=1)
    grouped["share"] = grouped["hires"] / max(grouped["hires"].sum(), 1)
    grouped = grouped.sort_values("hires", ascending=False).reset_index(drop=True)

    channels = grouped["group"].tolist()

    share_chart = viz.chart(
        "donut",
        "سهم هر کانال از استخدام‌های نهایی",
        channels,
        [viz.series("استخدام", grouped["hires"].tolist())],
        subtitle=f"مجموع {num(grouped['hires'].sum(), 0)} استخدام نهایی",
        y_label="نفر",
    )

    cost_chart = viz.chart(
        "bar",
        "هزینه کل و سرانه هر کانال",
        channels,
        [
            viz.series("هزینه کل", grouped["cost"], PALETTE[3]),
            viz.series("سرانه هر استخدام", grouped["cph"], PALETTE[0], kind="line"),
        ],
        subtitle="ستون‌ها هزینه کل و خط سرانه هر استخدام را نشان می‌دهد",
        y_label="هزینه",
        y_format="currency",
        options={"dualAxis": True},
    )

    parts = data.groupby("channel", observed=True)[[c for c, _ in COST_PARTS]].sum()
    parts = parts.reindex(channels).fillna(0)
    breakdown_chart = viz.chart(
        "bar",
        "تجزیه اجزای هزینه هر کانال",
        channels,
        [
            viz.series(label, parts[key].tolist(), PALETTE[i % len(PALETTE)])
            for i, (key, label) in enumerate(COST_PARTS)
        ],
        subtitle="سهم هر جزء هزینه از مجموع هزینه کانال",
        y_label="هزینه",
        y_format="currency",
        stacked=True,
    )

    rows = [
        {
            "group": r["group"],
            "applicants": int(r["applicants"]),
            "requisitions": int(r["requisitions"]),
            "hires": int(r["hires"]),
            "share": float(r["share"]),
            "cost": float(r["cost"]),
            "cph": float(r["cph"]),
            "conversion": safe_div(r["hires"], r["applicants"]),
        }
        for _, r in grouped.iterrows()
    ]

    cheapest = min(rows, key=lambda r: r["cph"])
    priciest = max(rows, key=lambda r: r["cph"])
    biggest = rows[0]

    insights = [
        viz.insight(
            f"کانال «{biggest['group']}» با {num(biggest['hires'], 0)} استخدام "
            f"({pct(biggest['share'])} از کل) بیشترین حجم را تأمین می‌کند.",
            "info",
            "بیشترین حجم",
        ),
        viz.insight(
            f"سرانه هزینه از {num(cheapest['cph'], 0)} در «{cheapest['group']}» تا {num(priciest['cph'], 0)} در "
            f"«{priciest['group']}» متغیر است — اختلاف {num(safe_div(priciest['cph'], cheapest['cph']), 1)} برابری.",
            "warn",
            "شکاف سرانه هزینه",
        ),
        viz.insight(
            "حجم بالا لزوماً به معنای صرفه اقتصادی یا کیفیت بالاتر نیست؛ "
            "برای سنجش همزمان حجم، هزینه و کیفیت، تحلیل تشخیصی «کیفیت در برابر حجم کانال جذب» را ببینید.",
            "info",
            "نکته تحلیلی",
        ),
    ]

    return viz.response(
        "d6",
        kpis=[
            viz.kpi("تعداد کانال فعال", len(channels), "number"),
            viz.kpi("ارزان‌ترین کانال", cheapest["cph"], "currency", cheapest["group"], "good"),
            viz.kpi("گران‌ترین کانال", priciest["cph"], "currency", priciest["group"], "warn"),
            viz.kpi("پرحجم‌ترین کانال", biggest["share"], "percent", biggest["group"]),
        ],
        insights=insights,
        charts=[share_chart, cost_chart, breakdown_chart],
        tables=[
            viz.table(
                "مقایسه تفصیلی کانال‌ها",
                [
                    viz.column("group", "کانال جذب", "text"),
                    viz.column("applicants", "داوطلب", "number"),
                    viz.column("requisitions", "تقاضا", "number"),
                    viz.column("hires", "استخدام نهایی", "number", bar=True),
                    viz.column("share", "سهم از استخدام", "percent"),
                    viz.column("conversion", "نرخ تبدیل داوطلب", "percent"),
                    viz.column("cost", "هزینه کل", "currency"),
                    viz.column("cph", "سرانه هر استخدام", "currency"),
                ],
                rows,
            )
        ],
        filters=_base_filters(df, keys=("department", "job_level", "recruiter")),
    )


# ═══════════════════════════ D7 ═══════════════════════════
def d7_offer_acceptance(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    if data.empty:
        return viz.response("d7", insights=[viz.insight("با فیلترهای انتخاب‌شده رکوردی یافت نشد.", "warn")])

    dimension = _pick(params, "slice", [t["value"] for t in SLICE_TABS], "job_level")
    overall = float(data["offer_accepted"].mean())

    grouped = rate_by(data, dimension, "offer_accepted")
    labels = grouped["group"].tolist()
    if dimension in ("job_level", "education"):
        ordered = order_categories(dimension, labels)
        grouped = grouped.set_index("group").reindex(ordered).reset_index()
        labels = grouped["group"].tolist()

    dim_label = DIMENSIONS[dimension]
    rate_chart = viz.chart(
        "bar",
        f"نرخ پذیرش پیشنهاد به تفکیک {dim_label}",
        labels,
        [viz.series("نرخ پذیرش", grouped["rate"], PALETTE[0])],
        subtitle="پیشنهادهای پذیرفته‌شده تقسیم بر کل پیشنهادها",
        y_label="نرخ",
        y_format="percent",
        annotations=[viz.threshold(overall, f"میانگین کل {pct(overall)}", "info")],
    )

    ts = monthly_series(data, {"rate": ("offer_accepted", "mean")}, "month")
    trend_chart = viz.chart(
        "line",
        "روند ماهانه نرخ پذیرش پیشنهاد",
        ts["label"].tolist(),
        [viz.series("نرخ پذیرش", ts["rate"], PALETTE[1])],
        subtitle="میانگین در هر ماه",
        y_label="نرخ",
        y_format="percent",
        annotations=[viz.threshold(overall, f"میانگین دوره {pct(overall)}", "info")],
    )

    # نرخ پذیرش بر حسب بازه شکاف حقوق: منفی یعنی پیشنهاد زیر بازار
    gap = data.dropna(subset=["salary_gap"]).copy()
    edges = [-1.0, -0.15, -0.10, -0.05, 0.0, 1.0]
    bucket_labels = [
        "زیر ۱۵٪ کمتر از بازار",
        "۱۰ تا ۱۵٪ کمتر",
        "۵ تا ۱۰٪ کمتر",
        "تا ۵٪ کمتر",
        "برابر یا بالاتر از بازار",
    ]
    gap["bucket"] = pd.cut(gap["salary_gap"], bins=edges, labels=bucket_labels, include_lowest=True)
    gap_stats = (
        gap.groupby("bucket", observed=False)["offer_accepted"]
        .agg(rate="mean", count="size")
        .reindex(bucket_labels)
    )
    gap_chart = viz.chart(
        "bar",
        "نرخ پذیرش بر حسب شکاف حقوق پیشنهادی با بازار",
        bucket_labels,
        [viz.series("نرخ پذیرش", gap_stats["rate"].fillna(0).tolist(), PALETTE[2])],
        subtitle="هرچه پیشنهاد به سطح بازار نزدیک‌تر باشد، احتمال پذیرش بالاتر است",
        y_label="نرخ",
        y_format="percent",
        annotations=[viz.threshold(overall, f"میانگین کل {pct(overall)}", "info")],
        footnote="تعداد نمونه هر بازه: " + " · ".join(
            f"{lbl}: {int(gap_stats.loc[lbl, 'count'])}" for lbl in bucket_labels
            if not pd.isna(gap_stats.loc[lbl, "count"])
        ),
    )

    rows = [
        {
            "group": r["group"],
            "count": int(r["count"]),
            "accepted": int(r["events"]),
            "rate": float(r["rate"]),
            "vs_avg": float(r["rate"] - overall),
        }
        for _, r in grouped.iterrows()
    ]

    gap_corr = correlation(data["salary_gap"], data["offer_accepted"])
    ttf_corr = correlation(data["time_to_fill"], data["offer_accepted"])
    best = max(rows, key=lambda r: r["rate"])
    worst = min(rows, key=lambda r: r["rate"])

    insights = [
        viz.insight(
            f"نرخ پذیرش پیشنهاد در کل سازمان {pct(overall)} است.",
            "info",
            "نرخ کل",
        ),
        viz.insight(
            f"بالاترین نرخ در «{best['group']}» با {pct(best['rate'])} و پایین‌ترین در «{worst['group']}» "
            f"با {pct(worst['rate'])} — شکاف {num((best['rate'] - worst['rate']) * 100, 0)} واحد درصد.",
            "warn" if best["rate"] - worst["rate"] > 0.2 else "info",
            f"شکاف در {dim_label}",
        ),
        viz.insight(
            f"همبستگی شکاف حقوق با پذیرش {num(gap_corr, 2)} و همبستگی طول فرآیند با پذیرش {num(ttf_corr, 2)} است؛ "
            f"{'سطح حقوق پیشنهادی مؤثرترین عامل قابل کنترل است' if abs(gap_corr) > abs(ttf_corr) else 'کوتاه‌کردن فرآیند مؤثرتر از افزایش حقوق است'}.",
            "warn",
            "عوامل مؤثر",
        ),
    ]

    return viz.response(
        "d7",
        kpis=[
            viz.kpi("نرخ پذیرش کل", overall, "percent"),
            viz.kpi("کل پیشنهادها", int(len(data)), "number"),
            viz.kpi("بالاترین نرخ", best["rate"], "percent", best["group"], "good"),
            viz.kpi("پایین‌ترین نرخ", worst["rate"], "percent", worst["group"], "warn"),
        ],
        insights=insights,
        charts=[rate_chart, gap_chart, trend_chart],
        tables=[
            viz.table(
                f"جزئیات به تفکیک {dim_label}",
                [
                    viz.column("group", dim_label, "text"),
                    viz.column("count", "تعداد پیشنهاد", "number"),
                    viz.column("accepted", "پذیرفته‌شده", "number"),
                    viz.column("rate", "نرخ پذیرش", "percent", bar=True),
                    viz.column("vs_avg", "اختلاف با میانگین", "delta_percent_point"),
                ],
                rows,
            )
        ],
        filters=_base_filters(df),
        tabs=[viz.tab_spec("slice", "برش بر اساس", SLICE_TABS)],
    )


# ═══════════════════════════ D8 ═══════════════════════════
def d8_quality(df: pd.DataFrame, params: dict) -> dict:
    data = apply_filters(df, params)
    hired = data[data["hired"] == 1]
    if hired.empty:
        return viz.response("d8", insights=[viz.insight("با فیلترهای انتخاب‌شده هیچ استخدام نهایی وجود ندارد.", "warn")])

    dimension = _pick(params, "slice", [t["value"] for t in SLICE_TABS], "channel")
    dim_label = DIMENSIONS[dimension]

    satisfaction = float(hired["applicant_satisfaction"].mean())
    perf6 = float(hired["performance_score_6m"].mean())
    turnover1 = float(hired["first_year_turnover"].mean())
    turnover2 = float(hired["turnover_2y"].mean())

    sat = (
        hired.groupby(dimension, observed=True)["applicant_satisfaction"]
        .agg(mean="mean", count="size")
        .reset_index()
        .rename(columns={dimension: "group"})
        .sort_values("mean", ascending=False)
    )
    sat_chart = viz.chart(
        "bar",
        f"رضایت کارجویان از فرآیند — {dim_label}",
        sat["group"].tolist(),
        [viz.series("میانگین رضایت", sat["mean"], PALETTE[0])],
        subtitle="امتیاز از ۵",
        y_label="امتیاز",
        y_format="score",
        annotations=[viz.threshold(satisfaction, f"میانگین کل {num(satisfaction, 2)}", "info")],
    )

    turn = rate_by(hired, dimension, "first_year_turnover")
    turn_chart = viz.chart(
        "bar",
        f"نرخ خروج در سال اول — {dim_label}",
        turn["group"].tolist(),
        [viz.series("نرخ خروج سال اول", turn["rate"], PALETTE[2])],
        subtitle="هرچه کمتر، ماندگاری استخدام بهتر",
        y_label="نرخ",
        y_format="percent",
        annotations=[viz.threshold(turnover1, f"میانگین کل {pct(turnover1)}", "info")],
    )

    perf = (
        hired.groupby(dimension, observed=True)[
            ["performance_score_6m", "performance_score_1y", "performance_score_2y"]
        ]
        .mean()
        .reset_index()
        .rename(columns={dimension: "group"})
    )
    perf_chart = viz.chart(
        "bar",
        f"اثربخشی استخدام‌های جدید — {dim_label}",
        perf["group"].tolist(),
        [
            viz.series("عملکرد ۶ ماهه", perf["performance_score_6m"], PALETTE[0]),
            viz.series("عملکرد یک ساله", perf["performance_score_1y"], PALETTE[1]),
            viz.series("عملکرد دو ساله", perf["performance_score_2y"], PALETTE[4]),
        ],
        subtitle="میانگین نمره عملکرد از ۱۰۰",
        y_label="نمره",
    )

    exit_months = hired["turnover_month_2y"].dropna()
    charts = [sat_chart, turn_chart, perf_chart]
    if not exit_months.empty:
        labels, counts, _ = histogram(exit_months, bins=min(12, max(4, int(exit_months.nunique()))))
        charts.append(
            viz.chart(
                "histogram",
                "توزیع ماه خروج کارکنان",
                labels,
                [viz.series("تعداد خروج", counts, PALETTE[2])],
                subtitle="ماه‌های ابتدایی خدمت که بیشترین خروج در آنها رخ داده است",
                y_label="تعداد",
                x_label="ماه خدمت",
            )
        )

    rows = []
    for group in sat["group"].tolist():
        subset = hired[hired[dimension] == group]
        rows.append(
            {
                "group": group,
                "hires": int(len(subset)),
                "satisfaction": float(subset["applicant_satisfaction"].mean()),
                "perf6": float(subset["performance_score_6m"].mean()),
                "perf1y": float(subset["performance_score_1y"].mean()),
                "turnover1": float(subset["first_year_turnover"].mean()),
                "turnover2": float(subset["turnover_2y"].mean()),
            }
        )

    best_sat = max(rows, key=lambda r: r["satisfaction"])
    worst_turn = max(rows, key=lambda r: r["turnover1"])
    best_turn = min(rows, key=lambda r: r["turnover1"])
    sat_perf_corr = correlation(hired["applicant_satisfaction"], hired["performance_score_6m"])
    interview_corr = correlation(hired["interview_score"], hired["performance_score_6m"])

    insights = [
        viz.insight(
            f"میانگین رضایت کارجویان {num(satisfaction, 2)} از ۵ است و بالاترین رضایت در "
            f"«{best_sat['group']}» با {num(best_sat['satisfaction'], 2)} ثبت شده است.",
            "good" if satisfaction >= 3.5 else "warn",
            "رضایت کارجو",
        ),
        viz.insight(
            f"نرخ خروج سال اول {pct(turnover1)} و تا پایان سال دوم {pct(turnover2)} است. "
            f"بدترین وضعیت در «{worst_turn['group']}» با {pct(worst_turn['turnover1'])} در برابر "
            f"«{best_turn['group']}» با {pct(best_turn['turnover1'])} — اختلاف "
            f"{num(safe_div(worst_turn['turnover1'], best_turn['turnover1']), 1)} برابری.",
            "bad" if worst_turn["turnover1"] > 0.2 else "warn",
            "ماندگاری",
        ),
        viz.insight(
            f"همبستگی نمره مصاحبه با عملکرد ۶ ماهه {num(interview_corr, 2)} و همبستگی رضایت کارجو با عملکرد "
            f"{num(sat_perf_corr, 2)} است؛ "
            f"{'ارزیابی مرحله جذب پیش‌بینی‌کننده معناداری برای عملکرد بعدی است' if interview_corr > 0.3 else 'ارزیابی مرحله جذب ارتباط ضعیفی با عملکرد بعدی دارد'}.",
            "info",
            "اعتبار ارزیابی جذب",
        ),
    ]

    return viz.response(
        "d8",
        kpis=[
            viz.kpi("رضایت کارجویان", satisfaction, "score", "میانگین امتیاز از ۵", "good" if satisfaction >= 3.5 else "warn"),
            viz.kpi("عملکرد ۶ ماهه", perf6, "number", "میانگین نمره از ۱۰۰"),
            viz.kpi("خروج سال اول", turnover1, "percent", tone="warn"),
            viz.kpi("خروج تا دو سال", turnover2, "percent", tone="warn"),
        ],
        insights=insights,
        charts=charts,
        tables=[
            viz.table(
                f"کیفیت استخدام به تفکیک {dim_label}",
                [
                    viz.column("group", dim_label, "text"),
                    viz.column("hires", "استخدام نهایی", "number"),
                    viz.column("satisfaction", "رضایت کارجو", "score", bar=True),
                    viz.column("perf6", "عملکرد ۶ ماهه", "number"),
                    viz.column("perf1y", "عملکرد یک ساله", "number"),
                    viz.column("turnover1", "خروج سال اول", "percent"),
                    viz.column("turnover2", "خروج تا دو سال", "percent"),
                ],
                rows,
                footnote=f"محاسبه روی {num(len(hired), 0)} رکورد استخدام‌شده انجام شده است.",
            )
        ],
        filters=_base_filters(df),
        tabs=[viz.tab_spec("slice", "برش بر اساس", SLICE_TABS)],
    )


HANDLERS = {
    "d1": d1_demand_trend,
    "d2": d2_composition,
    "d3": d3_time_to_fill,
    "d4": d4_funnel,
    "d5": d5_cost_per_hire,
    "d6": d6_channels,
    "d7": d7_offer_acceptance,
    "d8": d8_quality,
}
