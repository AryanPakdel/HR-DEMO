// قالب‌بندی اعداد و متن‌ها به فارسی

const FA_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];

export let CURRENCY = 'ریال';
export function setCurrency(label) {
  if (label) CURRENCY = label;
}

/**
 * تبدیل ارقام لاتین یک رشته به ارقام فارسی.
 * ممیز و جداکننده هزارگان فقط وقتی فارسی می‌شوند که بین دو رقم باشند، تا نقطه پایان
 * جمله یا ویرگول فهرست دست‌نخورده بماند.
 */
export function fa(text) {
  return String(text)
    .replace(/(\d)\.(\d)/g, '$1٫$2')
    .replace(/(\d),(\d)/g, '$1٬$2')
    .replace(/\d/g, (d) => FA_DIGITS[+d]);
}

/** جداکننده هزارگان با ارقام فارسی */
export function group(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const fixed = Number(value).toFixed(digits);
  const [intPart, decPart] = fixed.split('.');
  const withSep = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '٬');
  return fa(decPart ? `${withSep}٫${decPart}` : withSep);
}

/** خلاصه‌سازی مبالغ بزرگ: ۱۲٫۳ میلیون */
export function money(value, { compact = true, unit = true } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const n = Number(value);
  const abs = Math.abs(n);
  const suffix = unit ? ` ${CURRENCY}` : '';
  if (!compact || abs < 1e6) return group(Math.round(n)) + suffix;
  if (abs < 1e9) return `${group(n / 1e6, 1)} میلیون${suffix}`;
  if (abs < 1e12) return `${group(n / 1e9, 2)} میلیارد${suffix}`;
  return `${group(n / 1e12, 2)} هزار میلیارد${suffix}`;
}

export function percent(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${group(Number(value) * 100, digits)}٪`;
}

export function days(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${group(value, digits)} روز`;
}

export function score(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return group(value, digits);
}

/**
 * قالب‌بندی یک مقدار بر پایه نوع اعلام‌شده در قرارداد پاسخ بک‌اند.
 * حالت compact برای برچسب‌های محور نمودار استفاده می‌شود.
 */
export function formatValue(value, kind = 'number', { compact = false } = {}) {
  if (value === null || value === undefined || value === '') return '—';
  if (kind === 'text' || kind === 'badge' || typeof value === 'string') return fa(value);
  const n = Number(value);
  if (Number.isNaN(n)) return fa(value);

  switch (kind) {
    case 'percent':
      return percent(n, compact ? 0 : 1);
    case 'delta_percent':
      return (n >= 0 ? '+' : '−') + percent(Math.abs(n), 1);
    case 'delta_percent_point':
      return (n >= 0 ? '+' : '−') + group(Math.abs(n) * 100, 1) + ' واحد';
    case 'days':
      return compact ? group(n, n < 10 ? 1 : 0) : days(n, 1);
    case 'delta_days':
      return (n >= 0 ? '+' : '−') + group(Math.abs(n), 1) + (compact ? '' : ' روز');
    case 'currency':
      return compact ? moneyCompact(n) : money(n);
    case 'score':
      return score(n, 2);
    case 'number':
    default:
      if (Number.isInteger(n)) return group(n);
      return group(n, Math.abs(n) < 10 ? (Math.abs(n) < 1 ? 3 : 2) : 1);
  }
}

/** نسخه کوتاه مبلغ برای محور نمودار، بدون نام واحد پول */
function moneyCompact(n) {
  const abs = Math.abs(n);
  if (abs >= 1e9) return `${group(n / 1e9, 1)} م‌د`;
  if (abs >= 1e6) return `${group(n / 1e6, abs < 1e7 ? 1 : 0)} م`;
  if (abs >= 1e3) return `${group(n / 1e3, 0)} هـ`;
  return group(n);
}

/** جدا کردن عدد و واحد برای نمایش در کارت KPI */
export function splitUnit(value, kind) {
  if (kind === 'text' || typeof value === 'string') return { value: fa(value), unit: '' };
  const n = Number(value);
  if (Number.isNaN(n)) return { value: '—', unit: '' };
  switch (kind) {
    case 'percent':
      return { value: group(n * 100, 1), unit: '٪' };
    case 'days':
      return { value: group(n, 1), unit: 'روز' };
    case 'currency': {
      const abs = Math.abs(n);
      if (abs >= 1e9) return { value: group(n / 1e9, 2), unit: `میلیارد ${CURRENCY}` };
      if (abs >= 1e6) return { value: group(n / 1e6, 1), unit: `میلیون ${CURRENCY}` };
      return { value: group(n), unit: CURRENCY };
    }
    case 'score':
      return { value: group(n, 2), unit: '' };
    default:
      return { value: formatValue(n, kind), unit: '' };
  }
}

/** برچسب کوتاه محور: نام ماه از «سال ۱ · مهر» */
export function shortLabel(label, maxLength = 14) {
  const text = String(label);
  if (text.length <= maxLength) return fa(text);
  return `${fa(text.slice(0, maxLength - 1))}…`;
}

export function toneClass(prefix, tone) {
  return tone && tone !== 'neutral' ? `${prefix} ${prefix}--${tone}` : prefix;
}
