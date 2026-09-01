"""تحلیل سطح پیش‌بینی: مدل زمان پر شدن پست و اهمیت عوامل.

مدل تنها از ویژگی‌هایی استفاده می‌کند که پیش از شروع فرآیند جذب معلوم‌اند، تا
پیش‌بینی برای یک پست تازه‌باز معتبر باشد. روزهای پردازش منابع انسانی و تأیید مدیر
عمداً کنار گذاشته شده‌اند چون خودشان بخشی از زمان پر شدن‌اند و استفاده از آنها
نشت اطلاعات (leakage) ایجاد می‌کند.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .. import viz
from ..ingest import dimension_options, safe_div
from ..schema import DIMENSIONS, JOB_LEVEL_ORDER, PERSIAN_MONTHS, SEASON_LABELS
from .common import PALETTE, num, outlier_threshold, pct, relative

CATEGORICAL_FEATURES = ["department", "job_level", "channel", "recruiter"]
NUMERIC_FEATURES = ["month_no", "season", "concurrent_openings"]
FEATURE_LABELS = {
    "department": "واحد سازمانی",
    "job_level": "سطح شغلی",
    "channel": "کانال جذب",
    "recruiter": "کارشناس جذب",
    "month_no": "ماه سال",
    "season": "فصل",
    "concurrent_openings": "تعداد پست همزمان باز در واحد",
}
TARGET = "time_to_fill"
RANDOM_STATE = 42
TEST_SIZE = 0.2


def _make_pipeline(**kwargs) -> Pipeline:
    encoder = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES)],
        remainder="passthrough",
    )
    # عمق ۲ عمداً انتخاب شده: اثر ابعاد سازمانی روی زمان پر شدن عمدتاً جمع‌پذیر است و
    # درخت‌های عمیق‌تر روی این حجم داده فقط بیش‌برازش می‌کنند (R² اعتبارسنجی متقابل پایین‌تر).
    model = GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=2,
        random_state=RANDOM_STATE,
        **kwargs,
    )
    return Pipeline([("encode", encoder), ("model", model)])


def train_model(df: pd.DataFrame) -> dict:
    """آموزش مدل نقطه‌ای و دو مدل چندکی، به همراه سنجه‌های اعتبارسنجی."""
    features = CATEGORICAL_FEATURES + NUMERIC_FEATURES
    data = df.dropna(subset=[TARGET] + features)
    X, y = data[features], data[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    point = _make_pipeline().fit(X_train, y_train)
    lower = _make_pipeline(loss="quantile", alpha=0.10).fit(X_train, y_train)
    upper = _make_pipeline(loss="quantile", alpha=0.90).fit(X_train, y_train)

    pred_test = point.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, pred_test)))

    importance = permutation_importance(
        point, X_test, y_test, n_repeats=15, random_state=RANDOM_STATE, scoring="r2"
    )
    ranked = sorted(
        (
            {
                "feature": f,
                "label": FEATURE_LABELS[f],
                "importance": float(max(0.0, importance.importances_mean[i])),
                "std": float(importance.importances_std[i]),
            }
            for i, f in enumerate(features)
        ),
        key=lambda d: d["importance"],
        reverse=True,
    )
    total_importance = sum(d["importance"] for d in ranked) or 1.0
    for item in ranked:
        item["share"] = item["importance"] / total_importance

    # پوشش واقعی بازه اطمینان روی داده تست
    lo_test, hi_test = lower.predict(X_test), upper.predict(X_test)
    coverage = float(np.mean((y_test >= lo_test) & (y_test <= hi_test)))

    mean_ttf, std_ttf, threshold_value = outlier_threshold(df, TARGET, sigmas=1.0)

    return {
        "point": point,
        "lower": lower,
        "upper": upper,
        "features": features,
        "metrics": {
            "r2": float(r2_score(y_test, pred_test)),
            "mae": float(mean_absolute_error(y_test, pred_test)),
            "rmse": rmse,
            "train_size": int(len(X_train)),
            "test_size": int(len(X_test)),
            "coverage": coverage,
            "target_mean": mean_ttf,
            "target_std": std_ttf,
            "threshold": threshold_value,
        },
        "importance": ranked,
        "scatter": {
            "actual": [float(v) for v in y_test.tolist()],
            "predicted": [float(v) for v in pred_test.tolist()],
        },
        "defaults": _defaults(df),
        "options": _options(df),
    }


def _options(df: pd.DataFrame) -> dict:
    return {
        "department": dimension_options(df, "department"),
        "job_level": dimension_options(df, "job_level", JOB_LEVEL_ORDER),
        "channel": dimension_options(df, "channel"),
        "recruiter": dimension_options(df, "recruiter"),
        "month": [m for m in PERSIAN_MONTHS if m in set(df["month"].dropna().tolist())] or PERSIAN_MONTHS,
    }


def _defaults(df: pd.DataFrame) -> dict:
    """مقادیر پیش‌فرض فرم: پرتکرارترین حالت هر بعد."""
    return {
        "department": str(df["department"].mode().iloc[0]),
        "job_level": str(df["job_level"].mode().iloc[0]),
        "channel": str(df["channel"].mode().iloc[0]),
        "recruiter": str(df["recruiter"].mode().iloc[0]),
        "month": str(df["month"].mode().iloc[0]),
        "concurrent_openings": int(round(df["concurrent_openings"].median())),
    }


def predict(bundle: dict, payload: dict) -> dict:
    """پیش‌بینی برای یک پست تازه‌باز به همراه بازه اطمینان ۸۰٪."""
    defaults = bundle["defaults"]
    month_name = payload.get("month") or defaults["month"]
    month_no = PERSIAN_MONTHS.index(month_name) if month_name in PERSIAN_MONTHS else 0

    try:
        concurrent = int(payload.get("concurrent_openings", defaults["concurrent_openings"]))
    except (TypeError, ValueError):
        concurrent = defaults["concurrent_openings"]
    concurrent = max(1, min(concurrent, 60))

    row = pd.DataFrame(
        [
            {
                "department": payload.get("department") or defaults["department"],
                "job_level": payload.get("job_level") or defaults["job_level"],
                "channel": payload.get("channel") or defaults["channel"],
                "recruiter": payload.get("recruiter") or defaults["recruiter"],
                "month_no": month_no,
                "season": month_no // 3,
                "concurrent_openings": concurrent,
            }
        ]
    )[bundle["features"]]

    days = float(bundle["point"].predict(row)[0])
    lo = float(bundle["lower"].predict(row)[0])
    hi = float(bundle["upper"].predict(row)[0])
    lo, hi = min(lo, days), max(hi, days)

    metrics = bundle["metrics"]
    over_threshold = days > metrics["threshold"]

    if over_threshold:
        tone, verdict = "bad", "بالاتر از آستانه بحرانی"
    elif days > metrics["target_mean"]:
        tone, verdict = "warn", "کندتر از میانگین سازمان"
    else:
        tone, verdict = "good", "سریع‌تر از میانگین سازمان"

    message = (
        f"این پست به‌طور تخمینی {num(days)} روز تا پر شدن زمان می‌برد "
        f"(بازه اطمینان ۸۰٪: {num(lo)} تا {num(hi)} روز) — "
        f"{relative(days, metrics['target_mean'])} از میانگین {num(metrics['target_mean'])} روزه سازمان."
    )
    if over_threshold:
        message += (
            f" این مقدار از آستانه بحرانی {num(metrics['threshold'])} روز عبور می‌کند؛ "
            "پیشنهاد می‌شود کانال جذب یا تخصیص کارشناس بازبینی شود."
        )

    return {
        "days": days,
        "lower": lo,
        "upper": hi,
        "month": month_name,
        "concurrent_openings": concurrent,
        "vs_average": days - metrics["target_mean"],
        "vs_average_pct": safe_div(days - metrics["target_mean"], metrics["target_mean"]),
        "threshold": metrics["threshold"],
        "overThreshold": over_threshold,
        "tone": tone,
        "verdict": verdict,
        "message": message,
    }


# شناسه‌هایی که به فرانت‌اند می‌گویند کدام کارت و کدام بند تحلیل با تغییر فرم به‌روز می‌شوند
LIVE_TAG = "prediction"


def live_kpis(result: dict) -> list[dict]:
    """دو کارت شاخصی که مستقیماً از خروجی مدل می‌آیند و با هر بار پیش‌بینی تغییر می‌کنند."""
    return [
        {
            **viz.kpi("زمان پیش‌بینی‌شده", result["days"], "days", result["verdict"], result["tone"]),
            "live": LIVE_TAG,
        },
        {
            **viz.kpi(
                "بازه اطمینان ۸۰٪",
                result["upper"],
                "days",
                f"از {num(result['lower'])} روز",
            ),
            "live": LIVE_TAG,
        },
    ]


def live_insight(result: dict) -> dict:
    return {**viz.insight(result["message"], result["tone"], "نتیجه پیش‌بینی"), "live": LIVE_TAG}


def predict_payload(bundle: dict, payload: dict) -> dict:
    """خروجی کامل نقطه پایانی پیش‌بینی: عددها به‌همراه کارت‌ها و متن آماده نمایش."""
    result = predict(bundle, payload)
    return {**result, "kpis": live_kpis(result), "insight": live_insight(result)}


# ═══════════════════════════ P1 ═══════════════════════════
def p1_time_to_fill_forecast(df: pd.DataFrame, params: dict, bundle: dict) -> dict:
    metrics = bundle["metrics"]
    importance = bundle["importance"]
    result = predict(bundle, params)

    importance_chart = viz.chart(
        "hbar",
        "اهمیت عوامل مؤثر بر زمان پر شدن پست",
        [d["label"] for d in importance],
        [viz.series("سهم از قدرت پیش‌بینی", [d["share"] for d in importance], PALETTE[0])],
        subtitle="اهمیت جایگشتی (Permutation Importance) روی داده تست",
        y_label="سهم",
        y_format="percent",
        highlight=[0],
        options={"highlightTone": "accent"},
    )

    actual = bundle["scatter"]["actual"]
    predicted = bundle["scatter"]["predicted"]
    lo_axis = min(min(actual), min(predicted))
    hi_axis = max(max(actual), max(predicted))
    scatter = viz.chart(
        "scatter",
        "مقدار واقعی در برابر پیش‌بینی مدل روی داده تست",
        [],
        [
            viz.series(
                "پست‌های مجموعه تست",
                [{"x": a, "y": p} for a, p in zip(actual, predicted)],
                PALETTE[1],
            )
        ],
        subtitle="هرچه نقاط به خط چین نزدیک‌تر باشند، پیش‌بینی دقیق‌تر است",
        x_label="زمان واقعی (روز)",
        y_label="زمان پیش‌بینی‌شده (روز)",
        options={"identityLine": True, "domain": [lo_axis, hi_axis], "pointRadius": 3},
    )

    rows = [
        {
            "label": d["label"],
            "share": d["share"],
            "importance": d["importance"],
            "std": d["std"],
        }
        for d in importance
    ]

    top = importance[0]
    controllable = next((d for d in importance if d["feature"] in ("channel", "recruiter")), None)

    insights = [
        live_insight(result),
        viz.insight(
            f"مدل روی {num(metrics['test_size'], 0)} رکورد کنارگذاشته‌شده به ضریب تعیین "
            f"{num(metrics['r2'], 3)} و خطای مطلق میانگین {num(metrics['mae'])} روز رسیده است. "
            f"بازه اطمینان ۸۰٪ در عمل {pct(metrics['coverage'])} از موارد تست را پوشش داده است.",
            "good" if metrics["r2"] > 0.6 else "warn",
            "اعتبار مدل",
        ),
        viz.insight(
            f"مؤثرترین عامل «{top['label']}» با {pct(top['share'])} از قدرت پیش‌بینی مدل است."
            + (
                f" در میان عوامل قابل کنترل سازمان، «{controllable['label']}» با {pct(controllable['share'])} "
                "بیشترین اثر را دارد و اهرم اصلی کوتاه‌کردن زمان پر شدن پست به شمار می‌رود."
                if controllable
                else ""
            ),
            "info",
            "اهرم‌های بهبود",
        ),
        viz.insight(
            "مدل عمداً از روزهای پردازش منابع انسانی و تأیید مدیر استفاده نمی‌کند، چون این دو خودشان بخشی از "
            "زمان پر شدن‌اند و ورودشان باعث نشت اطلاعات و خوش‌بینی کاذب مدل می‌شود. همه ویژگی‌های به‌کاررفته "
            "پیش از شروع فرآیند جذب معلوم‌اند.",
            "info",
            "طراحی ویژگی‌ها",
        ),
    ]

    return viz.response(
        "p1",
        kpis=[
            *live_kpis(result),
            viz.kpi("ضریب تعیین مدل", metrics["r2"], "number", "R² روی داده تست", "good" if metrics["r2"] > 0.6 else "warn"),
            viz.kpi("خطای مطلق میانگین", metrics["mae"], "days", "MAE روی داده تست"),
        ],
        insights=insights,
        charts=[importance_chart, scatter],
        tables=[
            viz.table(
                "رتبه‌بندی اهمیت عوامل",
                [
                    viz.column("label", "عامل", "text"),
                    viz.column("share", "سهم از قدرت پیش‌بینی", "percent", bar=True),
                    viz.column("importance", "افت ضریب تعیین در صورت حذف", "number"),
                    viz.column("std", "انحراف معیار برآورد", "number"),
                ],
                rows,
                footnote="اهمیت جایگشتی: مقدار هر ویژگی به‌طور تصادفی جابه‌جا و افت دقت مدل اندازه‌گیری می‌شود.",
            )
        ],
        extra={
            "prediction": result,
            "model": {
                "algorithm": "Gradient Boosting Regressor",
                "quantile": "رگرسیون چندکی برای بازه ۱۰٪ تا ۹۰٪",
                "split": f"تفکیک {int((1 - TEST_SIZE) * 100)}/{int(TEST_SIZE * 100)} آموزش و آزمون",
                "metrics": metrics,
                "featureLabels": FEATURE_LABELS,
            },
            "form": {
                "options": bundle["options"],
                "defaults": bundle["defaults"],
                "labels": {**DIMENSIONS, "month": "ماه شروع فرآیند", "concurrent_openings": "تعداد پست همزمان باز در واحد"},
                "seasons": SEASON_LABELS,
            },
        },
    )
