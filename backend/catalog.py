"""رجیستری ۱۴ سؤال تحلیلی: فراداده نمایشی و اتصال به تابع محاسبه."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

LEVELS = [
    {
        "key": "descriptive",
        "label": "تحلیل توصیفی",
        "question": "چه اتفاقی افتاده است؟",
        "description": "تصویر وضعیت موجود جذب و استخدام بر پایه داده ثبت‌شده",
    },
    {
        "key": "diagnostic",
        "label": "تحلیل تشخیصی",
        "question": "چرا این اتفاق افتاده است؟",
        "description": "ریشه‌یابی علت‌ها، شناسایی گلوگاه‌ها و مقایسه گروه‌های پرت",
    },
    {
        "key": "predictive",
        "label": "تحلیل پیش‌بینی",
        "question": "چه اتفاقی رخ خواهد داد؟",
        "description": "مدل‌سازی روی داده تاریخی برای برآورد وضعیت آینده",
    },
]


@dataclass
class Question:
    id: str
    level: str
    title: str
    question: str
    metric: str
    method: str
    charts: list[str]
    source: str
    icon: str
    compute: Callable | None = None
    preview: str = ""
    footnote: str = ""
    tags: list[str] = field(default_factory=list)

    def meta(self) -> dict:
        return {
            "id": self.id,
            "level": self.level,
            "title": self.title,
            "question": self.question,
            "metric": self.metric,
            "method": self.method,
            "charts": self.charts,
            "source": self.source,
            "icon": self.icon,
            "preview": self.preview,
            "footnote": self.footnote,
            "tags": self.tags,
        }


QUESTIONS: list[Question] = [
    # ─────────────────────────── توصیفی ───────────────────────────
    Question(
        id="d1",
        level="descriptive",
        title="تقاضای جذب و روند نیروی انسانی",
        question="تقاضای جذب نیروی انسانی در واحدهای زمانی ماهانه، فصلی و سالانه چقدر بوده و روند نیروی جذب‌شده چگونه تغییر کرده است؟",
        metric="Total Requisition · New Hires · Net Movement",
        method="تجمیع تعداد درخواست و استخدام در سطح ماه، فصل و سال؛ محاسبه نیروی خالص افزوده به‌صورت تجمعی",
        charts=["line", "area", "table"],
        source="شیت توصیفی ردیف ۱ · شیت Headcount ردیف ۵، ۶ و ۷",
        icon="trend",
        preview="۳۶ ماه روند",
        footnote="این صفحه روند «جذب» را نشان می‌دهد، نه موجودی کل نیروی انسانی سازمان؛ داده ورودی فقط رکوردهای جذب را در بر دارد.",
        tags=["تقاضا", "روند", "استخدام", "خروج"],
    ),
    Question(
        id="d2",
        level="descriptive",
        title="ترکیب جذب: واحد، سطح شغلی و مدرک تحصیلی",
        question="تقاضا و استخدام به تفکیک واحد سازمانی، سطح شغلی و مدرک تحصیلی چگونه توزیع شده است؟",
        metric="Requisition & Hire Distribution",
        method="شمارش و محاسبه سهم درصدی هر دسته از کل، و تقاطع واحد سازمانی با سطح شغلی",
        charts=["bar", "donut", "grouped"],
        source="شیت توصیفی ردیف ۲ · شیت Headcount ردیف ۳ و ۴",
        icon="layers",
        preview="۴ واحد · ۳ سطح",
        footnote="نوع استخدام (رسمی، پیمانی، قراردادی) در داده ورودی وجود ندارد؛ تفکیک بر پایه مدرک تحصیلی و سطح شغلی انجام شده است.",
        tags=["توزیع", "واحد سازمانی", "مدرک"],
    ),
    Question(
        id="d3",
        level="descriptive",
        title="زمان پر شدن پست (Time to Fill)",
        question="مدت زمان مورد نیاز برای پر شدن شغل‌ها و پست‌ها به چه میزان است و در واحدها و مشاغل مختلف چه تفاوتی دارد؟",
        metric="Time to Fill",
        method="میانگین، میانه و توزیع تعداد روز تا پر شدن پست، به تفکیک هر بعد سازمانی",
        charts=["histogram", "hbar", "line"],
        source="شیت توصیفی ردیف ۴ و ۵",
        icon="clock",
        preview="میانگین روز",
        tags=["زمان", "کارایی فرآیند"],
    ),
    Question(
        id="d4",
        level="descriptive",
        title="قیف استخدام، نرخ انتخاب و داوطلب به ازای پست",
        question="قیف استخدام در سازمان چگونه است، نرخ انتخاب نهایی کارجویان چقدر است و هر پست چند داوطلب جذب می‌کند؟",
        metric="Recruitment Funnel · Selection Rate · Applicants per Opening",
        method="تجمیع شش مرحله قیف و محاسبه نرخ تبدیل هر مرحله نسبت به مرحله قبل و نسبت به ورودی",
        charts=["funnel", "bar", "table"],
        source="شیت توصیفی ردیف ۱۵، ۱۶، ۲۰ و ۲۱",
        icon="funnel",
        preview="۶ مرحله",
        tags=["قیف", "نرخ انتخاب", "داوطلب"],
    ),
    Question(
        id="d5",
        level="descriptive",
        title="سرانه هزینه هر استخدام (Cost per Hire)",
        question="هزینه استخدام برای هر شغل به‌طور میانگین چقدر است و بالاترین و پایین‌ترین هزینه در کدام مشاغل و واحدهاست؟",
        metric="Cost per Hire",
        method="مجموع هزینه هر گروه تقسیم بر تعداد استخدام نهایی همان گروه",
        charts=["bar", "hbar", "table"],
        source="شیت توصیفی ردیف ۱۰ و ۱۱",
        icon="cost",
        preview="سرانه هزینه",
        tags=["هزینه", "بودجه"],
    ),
    Question(
        id="d6",
        level="descriptive",
        title="کانال‌های جذب: حجم، هزینه و سرانه",
        question="تعداد افراد جذب‌شده از هر کانال چقدر است، هزینه هر کانال چقدر است و سرانه هزینه هر استخدام در هر کانال چگونه است؟",
        metric="Hiring Source · Sourcing Channel Cost · Sourcing Cost per New Hire",
        method="تجمیع حجم و هزینه به تفکیک کانال و تجزیه هزینه به اجزای تشکیل‌دهنده",
        charts=["donut", "bar", "stacked"],
        source="شیت توصیفی ردیف ۱۲، ۱۳ و ۱۴",
        icon="channel",
        preview="۴ کانال",
        tags=["کانال", "هزینه", "منبع‌یابی"],
    ),
    Question(
        id="d7",
        level="descriptive",
        title="نرخ پذیرش پیشنهاد شغلی",
        question="نرخ پذیرش شغل توسط افراد تأییدشده چقدر است و در مشاغل و سطوح مختلف چه تفاوتی دارد؟",
        metric="Offer Acceptance Rate",
        method="نسبت پیشنهادهای پذیرفته‌شده به کل پیشنهادها، به تفکیک هر بعد و بازه شکاف حقوق",
        charts=["bar", "line", "table"],
        source="شیت توصیفی ردیف ۱۷ و ۲۶",
        icon="handshake",
        preview="نرخ پذیرش",
        tags=["پیشنهاد شغلی", "پذیرش"],
    ),
    Question(
        id="d8",
        level="descriptive",
        title="کیفیت استخدام: رضایت، عملکرد و خروج سال اول",
        question="رضایت کارجویان از فرآیند، اثربخشی استخدام‌های جدید و نرخ خروج آنها در سال اول به چه میزان است؟",
        metric="Applicant Satisfaction · Hiring Effectiveness · First-Year Turnover",
        method="میانگین نمرات رضایت و عملکرد و نرخ خروج، محاسبه‌شده روی زیرمجموعه استخدام‌شده",
        charts=["bar", "line", "histogram"],
        source="شیت توصیفی ردیف ۲۲، ۲۳، ۲۴ و ۲۵",
        icon="quality",
        preview="کیفیت استخدام",
        footnote="شاخص‌های پس از استخدام فقط برای رکوردهایی محاسبه می‌شوند که به استخدام نهایی رسیده‌اند.",
        tags=["رضایت", "عملکرد", "ماندگاری"],
    ),
    # ─────────────────────────── تشخیصی ───────────────────────────
    Question(
        id="g1",
        level="diagnostic",
        title="ریشه‌یابی زمان پر شدن پست و تفکیک تأخیر",
        question="چرا زمان پر شدن پست‌ها در برخی واحدها بیشتر از میانگین است و این کندی ناشی از تأخیر منابع انسانی است یا تأخیر مدیر واحد درخواست‌کننده؟",
        metric="Time-to-Fill Root Cause · Stakeholder Delay Attribution",
        method="گروه‌بندی و محاسبه میانگین و انحراف معیار هر گروه؛ گروهی که میانگینش از «میانگین کل + یک انحراف معیار» بگذرد پرت علامت می‌خورد. سپس زمان کل به بازه‌های مسئولیت تجزیه می‌شود.",
        charts=["hbar", "stacked", "table"],
        source="شیت تحلیل تشخیصی ردیف ۱ و ۱۰",
        icon="search",
        preview="گروه‌های پرت",
        tags=["ریشه‌یابی", "پرت", "تأخیر"],
    ),
    Question(
        id="g2",
        level="diagnostic",
        title="گلوگاه قیف استخدام",
        question="در کدام مرحله از قیف استخدام بیشترین افت کاندیدا رخ می‌دهد و این الگو در واحدها و کانال‌های مختلف چه تفاوتی دارد؟",
        metric="Funnel Bottleneck / Drop-off Analysis",
        method="نرخ تبدیل هر مرحله = عبورکرده تقسیم بر ورودی همان مرحله؛ مرحله با کمترین نرخ تبدیل گلوگاه اصلی است. محاسبه به تفکیک هر بعد برای یافتن الگوهای متفاوت.",
        charts=["funnel", "heatmap", "table"],
        source="شیت تحلیل تشخیصی ردیف ۲",
        icon="bottleneck",
        preview="گلوگاه اصلی",
        tags=["قیف", "گلوگاه", "افت"],
    ),
    Question(
        id="g3",
        level="diagnostic",
        title="کیفیت در برابر حجم کانال جذب",
        question="کدام کانال جذب علاوه بر حجم بالا، کیفیت و ماندگاری استخدام پایدارتری هم تولید می‌کند؟",
        metric="Source Quality vs. Volume Analysis",
        method="محاسبه پنج شاخص برای هر کانال، نرمال‌سازی آنها و ترکیب با وزن‌های قابل تنظیم توسط کاربر به یک شاخص واحد",
        charts=["scatter", "bar", "table"],
        source="شیت تحلیل تشخیصی ردیف ۳",
        icon="balance",
        preview="وزن‌دهی تعاملی",
        tags=["کانال", "کیفیت", "شاخص ترکیبی"],
    ),
    Question(
        id="g4",
        level="diagnostic",
        title="ریشه‌یابی ترک خدمت زودهنگام",
        question="چه عواملی با نرخ بالای ترک خدمت در سال اول مرتبط هستند؟",
        metric="Early-Attrition Root-Cause Analysis",
        method="ساخت دو کوهورت «ماندگار» و «ترک‌کرده در سال اول» و محاسبه اختلاف میانگین یا نسبت هر متغیر بین دو گروه، مرتب‌شده بر شدت اختلاف",
        charts=["diffbar", "bar", "table"],
        source="شیت تحلیل تشخیصی ردیف ۵",
        icon="exit",
        preview="مقایسه دو کوهورت",
        footnote="تحلیل فقط روی رکوردهای استخدام‌شده که وضعیت سال اول آنها ثبت شده انجام می‌شود.",
        tags=["ترک خدمت", "کوهورت", "ماندگاری"],
    ),
    Question(
        id="g5",
        level="diagnostic",
        title="کارنامه عملکرد کارشناسان جذب",
        question="عملکرد کارشناسان جذب در شاخص‌های کلیدی چه تفاوتی دارد و علت آن چیست؟",
        metric="Recruiter Performance Benchmarking",
        method="محاسبه میانگین هر شاخص به تفکیک کارشناس و نرمال‌سازی با Z-score تا کارشناسان با حجم و نوع پست متفاوت منصفانه مقایسه شوند",
        charts=["radar", "bar", "table"],
        source="شیت تحلیل تشخیصی ردیف ۷",
        icon="scorecard",
        preview="۴ کارشناس",
        tags=["کارشناس جذب", "Z-score", "کارنامه"],
    ),
    # ─────────────────────────── پیش‌بینی ───────────────────────────
    Question(
        id="p1",
        level="predictive",
        title="پیش‌بینی زمان پر شدن پست و اهمیت عوامل",
        question="مدت زمان پر شدن یک پست جدید که تازه باز شده چقدر پیش‌بینی می‌شود و کدام عوامل بیشترین تأثیر را بر طولانی‌شدن آن دارند؟",
        metric="Time-to-Fill Forecasting Model · Feature Importance",
        method="آموزش Gradient Boosting روی داده تاریخی با ویژگی‌های از پیش معلوم، اعتبارسنجی با تفکیک ۸۰/۲۰ و ساخت بازه اطمینان ۸۰٪ با رگرسیون چندکی",
        charts=["gauge", "bar", "scatter"],
        source="شیت تحلیل پیش‌بینی ردیف ۱ و ۹",
        icon="forecast",
        preview="مدل تعاملی",
        footnote="مدل تنها از ویژگی‌هایی استفاده می‌کند که پیش از شروع فرآیند جذب معلوم‌اند تا پیش‌بینی برای پست تازه‌باز معتبر باشد.",
        tags=["پیش‌بینی", "رگرسیون", "اهمیت عوامل"],
    ),
]

QUESTION_BY_ID = {q.id: q for q in QUESTIONS}


def register(qid: str, fn: Callable) -> None:
    """اتصال تابع محاسبه به یک سؤال."""
    QUESTION_BY_ID[qid].compute = fn


def catalog_payload() -> dict:
    """فراداده کامل کاتالوگ برای صفحه فهرست سؤالات."""
    return {
        "levels": LEVELS,
        "questions": [q.meta() for q in QUESTIONS],
        "order": [q.id for q in QUESTIONS],
    }
