"""تعریف ثابت ساختار فایل داده جذب و استخدام و اعتبارسنجی آن."""

from __future__ import annotations

# واحد پول داده. اگر داده به تومان است این مقدار را تغییر دهید.
CURRENCY_LABEL = "ریال"

# ماه‌های شمسی به ترتیب تقویمی
PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]

SEASON_LABELS = ["بهار", "تابستان", "پاییز", "زمستان"]

# ستون‌های الزامی. هر ستون: (نام، نوع، برچسب فارسی)
NUMERIC_COLUMNS = [
    "id", "month_index", "year_no",
    "time_to_fill", "hr_processing_days", "manager_approval_days",
    "applicants", "screened", "interviewed", "tested", "offered", "accepted",
    "cost_ad", "cost_agency", "cost_referral", "cost_assessment",
    "cost_hr_time", "total_cost",
    "offer_accepted", "hired", "salary_gap", "years_experience",
    "interview_score", "technical_test_score",
    "first_year_turnover", "turnover_2y", "turnover_month_2y",
    "performance_score_6m", "performance_score_1y", "performance_score_2y",
    "applicant_satisfaction",
]

CATEGORICAL_COLUMNS = [
    "month", "department", "job_level", "channel", "recruiter", "education",
]

REQUIRED_COLUMNS = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS

# ستون‌هایی که فقط برای رکوردهای استخدام‌شده مقدار دارند
POST_HIRE_COLUMNS = [
    "first_year_turnover", "turnover_2y", "turnover_month_2y",
    "performance_score_6m", "performance_score_1y", "performance_score_2y",
    "applicant_satisfaction",
]

COLUMN_LABELS = {
    "id": "شناسه",
    "month_index": "شماره ماه از شروع",
    "year_no": "سال",
    "month": "ماه",
    "department": "واحد سازمانی",
    "job_level": "سطح شغلی",
    "channel": "کانال جذب",
    "recruiter": "کارشناس جذب",
    "education": "مدرک تحصیلی",
    "time_to_fill": "زمان پر شدن پست",
    "hr_processing_days": "روزهای پردازش منابع انسانی",
    "manager_approval_days": "روزهای تأیید مدیر واحد",
    "applicants": "داوطلبان",
    "screened": "غربال‌شده",
    "interviewed": "مصاحبه‌شده",
    "tested": "آزمون‌داده",
    "offered": "پیشنهاد دریافت‌کرده",
    "accepted": "پذیرفته",
    "cost_ad": "هزینه آگهی",
    "cost_agency": "هزینه مشاور",
    "cost_referral": "هزینه معرفی",
    "cost_assessment": "هزینه ارزیابی",
    "cost_hr_time": "هزینه زمان کارشناس",
    "total_cost": "هزینه کل",
    "offer_accepted": "پذیرش پیشنهاد",
    "hired": "استخدام نهایی",
    "salary_gap": "شکاف حقوق",
    "years_experience": "سابقه کاری",
    "interview_score": "نمره مصاحبه",
    "technical_test_score": "نمره آزمون فنی",
    "first_year_turnover": "خروج در سال اول",
    "turnover_2y": "خروج تا دو سال",
    "turnover_month_2y": "ماه خروج",
    "performance_score_6m": "عملکرد ۶ ماهه",
    "performance_score_1y": "عملکرد یک ساله",
    "performance_score_2y": "عملکرد دو ساله",
    "applicant_satisfaction": "رضایت کارجو",
}

# ابعادی که در فیلترها و گروه‌بندی‌ها استفاده می‌شوند
DIMENSIONS = {
    "department": "واحد سازمانی",
    "job_level": "سطح شغلی",
    "channel": "کانال جذب",
    "recruiter": "کارشناس جذب",
    "education": "مدرک تحصیلی",
}

# ترتیب معنادار سطح شغلی (از پایین به بالا)
JOB_LEVEL_ORDER = ["کارشناس", "سرپرست", "مدیر"]
EDUCATION_ORDER = ["کارشناسی", "کارشناسی ارشد", "دکتری"]

# مراحل قیف استخدام به ترتیب
FUNNEL_STAGES = [
    ("applicants", "داوطلبان"),
    ("screened", "غربال رزومه"),
    ("interviewed", "مصاحبه"),
    ("tested", "آزمون"),
    ("offered", "ارائه پیشنهاد"),
    ("accepted", "پذیرش نهایی"),
]


class SchemaError(Exception):
    """خطای ساختار فایل ورودی، همراه با جزئیات قابل نمایش به کاربر."""

    def __init__(self, message: str, missing: list[str] | None = None, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.missing = missing or []
        self.detail = detail

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "missing": [{"key": c, "label": COLUMN_LABELS.get(c, c)} for c in self.missing],
            "detail": self.detail,
        }


def validate_columns(columns) -> None:
    """اگر ستونی از ساختار مورد انتظار غایب باشد SchemaError پرتاب می‌کند."""
    present = {str(c).strip() for c in columns}
    missing = [c for c in REQUIRED_COLUMNS if c not in present]
    if missing:
        raise SchemaError(
            "ساختار فایل با ساختار مورد انتظار مطابقت ندارد.",
            missing=missing,
            detail=(
                f"از {len(REQUIRED_COLUMNS)} ستون لازم، {len(missing)} ستون در فایل یافت نشد. "
                "لطفاً فایل داده جذب و استخدام را بارگذاری کنید."
            ),
        )
