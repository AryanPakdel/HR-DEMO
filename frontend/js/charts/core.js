// موتور مشترک نمودارها: SVG دست‌ساز، بدون کتابخانه خارجی، سازگار با RTL

import { formatValue, fa, shortLabel } from '../format.js';

export const NS = 'http://www.w3.org/2000/svg';
export const SERIES_COLORS = ['--c1', '--c2', '--c3', '--c4', '--c5', '--c6'];

/** رنگ سری شماره i از پالت کیفی */
export function seriesColor(index, explicit) {
  if (explicit) return explicit;
  return `var(${SERIES_COLORS[index % SERIES_COLORS.length]})`;
}

export function el(tag, attrs = {}, children = []) {
  const node = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    node.setAttribute(key, String(value));
  }
  for (const child of [].concat(children)) {
    if (child) node.appendChild(child);
  }
  return node;
}

export function text(content, attrs = {}) {
  const node = el('text', {
    fill: 'var(--text-muted)',
    'font-size': 11,
    'font-family': 'var(--font)',
    ...attrs,
  });
  node.textContent = content;
  return node;
}

/**
 * ساخت بوم SVG واکنش‌گرا با viewBox.
 *
 * direction: ltr روی ریشه SVG تنظیم می‌شود چون در جهت rtl معنای text-anchor آینه می‌شود
 * (start به لبه راست و end به لبه چپ تبدیل می‌شود) و همه محاسبات مختصات این ماژول بر پایه
 * معنای متعارف ltr نوشته شده‌اند. unicode-bidi: plaintext جهت دوطرفه هر برچسب را از خود
 * متن تشخیص می‌دهد، بنابراین متن فارسی و ترکیب فارسی با عدد دقیقاً مثل قبل نمایش داده می‌شود.
 */
export function canvas(width, height) {
  return el('svg', {
    viewBox: `0 0 ${width} ${height}`,
    width: '100%',
    preserveAspectRatio: 'xMidYMid meet',
    role: 'img',
    style: 'direction:ltr;unicode-bidi:plaintext',
  });
}

/** انتخاب گام مناسب برای خطوط شبکه (۱، ۲، ۲٫۵، ۵ × توان ده) */
export function niceStep(range, targetTicks = 5) {
  if (range <= 0) return 1;
  const rough = range / targetTicks;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const normalized = rough / magnitude;
  let step = 1;
  if (normalized > 5) step = 10;
  else if (normalized > 2.5) step = 5;
  else if (normalized > 1.5) step = 2.5;
  else if (normalized > 1) step = 2;
  return step * magnitude;
}

/**
 * دامنه عمودی و مقادیر تیک.
 * includeZero برای نمودارهای ستونی الزامی است تا مقایسه طول‌ها گمراه‌کننده نشود.
 */
export function buildScale(values, { includeZero = true, targetTicks = 5, padTop = 0.08 } = {}) {
  const clean = values.filter((v) => v !== null && v !== undefined && Number.isFinite(v));
  if (!clean.length) return { min: 0, max: 1, ticks: [0, 1] };

  let min = Math.min(...clean);
  let max = Math.max(...clean);
  if (includeZero) {
    min = Math.min(0, min);
    max = Math.max(0, max);
  }
  if (min === max) {
    const pad = Math.abs(min) * 0.2 || 1;
    min -= pad;
    max += pad;
  } else {
    max += (max - min) * padTop;
  }

  const step = niceStep(max - min, targetTicks);
  const niceMin = Math.floor(min / step) * step;
  const niceMax = Math.ceil(max / step) * step;
  const ticks = [];
  // جمع اعشاری در حلقه انباشته می‌شود، پس تیک‌ها با ضرب ساخته می‌شوند
  const count = Math.round((niceMax - niceMin) / step);
  for (let i = 0; i <= count; i += 1) ticks.push(niceMin + i * step);

  return { min: niceMin, max: niceMax, ticks, step };
}

/** خطوط شبکه افقی و برچسب محور عمودی (سمت راست، مناسب RTL) */
export function yAxis(scale, plot, format, { showLabels = true } = {}) {
  const group = el('g');
  const toY = (v) => plot.y + plot.h - ((v - scale.min) / (scale.max - scale.min)) * plot.h;

  scale.ticks.forEach((tick) => {
    const y = toY(tick);
    group.appendChild(
      el('line', {
        x1: plot.x, x2: plot.x + plot.w, y1: y, y2: y,
        stroke: tick === 0 && scale.min < 0 ? 'var(--axis)' : 'var(--grid)',
        'stroke-width': 1,
      })
    );
    if (showLabels) {
      group.appendChild(
        text(formatValue(tick, format, { compact: true }), {
          x: plot.x + plot.w + 8, y: y + 3.5, 'text-anchor': 'start', 'font-size': 10.5,
          fill: 'var(--text-faint)',
        })
      );
    }
  });
  return { group, toY };
}

/**
 * برچسب‌های محور افقی با چرخش خودکار وقتی جا کم است.
 * در حالت چرخیده، برچسب حول نقطه لنگر می‌چرخد تا با محور فاصله ثابت بماند.
 */
export function xAxisLabels(categories, plot, bandWidth) {
  const group = el('g');
  const longest = categories.reduce((m, c) => Math.max(m, String(c).length), 0);
  // ~6.4px به ازای هر نویسه فارسی در اندازه ۱۱ پیکسل
  const rotate = longest * 6.4 > bandWidth * 0.95;
  // در حالت افقی، تعداد نویسه مجاز از پهنای واقعی باند محاسبه می‌شود تا برچسب‌ها
  // در نمودارهای کم‌دسته بی‌دلیل کوتاه نشوند
  const maxChars = rotate ? 20 : Math.max(6, Math.floor((bandWidth * 0.95) / 6.4));

  categories.forEach((label, i) => {
    const cx = plot.x + plot.w - (i + 0.5) * bandWidth; // راست به چپ
    const y = plot.y + plot.h + (rotate ? 12 : 16);
    const node = text(shortLabel(label, maxChars), {
      x: cx, y,
      'text-anchor': rotate ? 'end' : 'middle',
      'font-size': 10.5,
    });
    if (rotate) node.setAttribute('transform', `rotate(-38 ${cx} ${y})`);
    node.appendChild(titleTip(label));
    group.appendChild(node);
  });
  return { group, rotated: rotate };
}

/** فضای لازم زیر نمودار برای برچسب‌های محور افقی */
export function xLabelSpace(categories, bandWidth) {
  const longest = categories.reduce((m, c) => Math.max(m, String(c).length), 0);
  if (longest * 6.4 <= bandWidth * 0.95) return 26;
  return Math.min(96, 26 + Math.min(longest, 20) * 3.6);
}

/** عنوان بومی SVG برای نمایش متن کامل هنگام کوتاه‌شدن برچسب */
export function titleTip(content) {
  const node = el('title');
  node.textContent = fa(content);
  return node;
}

/* ─────────────────── تولتیپ مشترک ─────────────────── */
let tooltipNode = null;

function tooltipEl() {
  if (!tooltipNode) {
    tooltipNode = document.createElement('div');
    tooltipNode.className = 'tooltip';
    document.body.appendChild(tooltipNode);
  }
  return tooltipNode;
}

export function showTooltip(event, html) {
  const node = tooltipEl();
  node.innerHTML = html;
  node.classList.add('is-on');

  const rect = node.getBoundingClientRect();
  let left = event.clientX - rect.width - 14;
  if (left < 8) left = event.clientX + 14;
  let top = event.clientY - rect.height - 12;
  if (top < 8) top = event.clientY + 16;
  if (left + rect.width > window.innerWidth - 8) left = window.innerWidth - rect.width - 8;

  node.style.left = `${left}px`;
  node.style.top = `${top}px`;
}

export function hideTooltip() {
  if (tooltipNode) tooltipNode.classList.remove('is-on');
}

export function tooltipHtml(title, rows) {
  const body = rows
    .map(
      (r) =>
        `<div class="tooltip__row"><span>${
          r.color ? `<span class="tooltip__dot" style="background:${r.color}"></span>` : ''
        }${r.label}</span><b>${r.value}</b></div>`
    )
    .join('');
  return `<div class="tooltip__title">${fa(title)}</div>${body}`;
}

/** اتصال تولتیپ به یک شکل، همراه با دسترسی‌پذیری پایه */
export function attachTooltip(node, title, rows) {
  node.style.cursor = 'pointer';
  const html = tooltipHtml(title, rows);
  node.addEventListener('mouseenter', (e) => showTooltip(e, html));
  node.addEventListener('mousemove', (e) => showTooltip(e, html));
  node.addEventListener('mouseleave', hideTooltip);
  node.appendChild(
    titleTip(`${title} — ${rows.map((r) => `${r.label}: ${r.value}`).join(' · ')}`)
  );
}

/* ─────────────────── لجند ─────────────────── */
export function renderLegend(container, series, { onToggle } = {}) {
  if (series.length < 2) return null;
  const legend = document.createElement('div');
  legend.className = 'legend';

  series.forEach((s, i) => {
    const item = document.createElement('button');
    item.className = 'legend__item';
    item.type = 'button';
    item.innerHTML = `<span class="legend__swatch" style="background:${seriesColor(i, s.color)}"></span>${fa(s.name)}`;
    if (onToggle) {
      item.addEventListener('click', () => {
        item.classList.toggle('is-off');
        onToggle(i, !item.classList.contains('is-off'));
      });
    } else {
      item.style.cursor = 'default';
    }
    legend.appendChild(item);
  });

  container.appendChild(legend);
  return legend;
}

/** خط آستانه با برچسب */
export function drawAnnotations(group, annotations, plot, toY, format) {
  const lines = (annotations || [])
    .filter((a) => a.type === 'threshold')
    .map((a) => ({ ...a, y: toY(a.value) }))
    .filter((a) => Number.isFinite(a.y) && a.y >= plot.y - 1 && a.y <= plot.y + plot.h + 1)
    .sort((a, b) => a.y - b.y);

  // آستانه‌های نزدیک به هم، برچسب‌شان یکی بالا و یکی پایین خط می‌نشیند
  let lastY = -Infinity;
  let below = false;
  lines.forEach((a) => {
    const color = a.tone === 'warn' ? 'var(--warn)' : a.tone === 'bad' ? 'var(--bad)' : 'var(--info)';
    below = a.y - lastY < 16 ? !below : false;
    lastY = a.y;

    group.appendChild(
      el('line', {
        x1: plot.x, x2: plot.x + plot.w, y1: a.y, y2: a.y,
        stroke: color, 'stroke-width': 1.4, 'stroke-dasharray': '5 4', opacity: 0.85,
      })
    );
    group.appendChild(
      text(fa(a.label), {
        x: plot.x + 6, y: below ? a.y + 12 : a.y - 5,
        'text-anchor': 'start', 'font-size': 10, fill: color, 'font-weight': 500,
      })
    );
  });
}

/** خط آستانه عمودی برای نمودار میله‌ای افقی */
export function drawAnnotationsX(group, annotations, plot, toX) {
  const lines = (annotations || [])
    .filter((a) => a.type === 'threshold' && Number.isFinite(toX(a.value)))
    .map((a) => ({ ...a, x: toX(a.value) }))
    .sort((a, b) => a.x - b.x);

  // وقتی دو آستانه نزدیک هم باشند، برچسب‌ها روی دو سطر جدا می‌نشینند تا روی هم نیفتند
  let lastX = -Infinity;
  let row = 0;
  lines.forEach((a) => {
    const color = a.tone === 'warn' ? 'var(--warn)' : a.tone === 'bad' ? 'var(--bad)' : 'var(--info)';
    row = a.x - lastX < 120 ? 1 - row : 0;
    lastX = a.x;

    group.appendChild(
      el('line', {
        x1: a.x, x2: a.x, y1: plot.y - 4, y2: plot.y + plot.h,
        stroke: color, 'stroke-width': 1.4, 'stroke-dasharray': '5 4', opacity: 0.85,
      })
    );
    group.appendChild(
      text(fa(a.label), {
        x: a.x, y: plot.y - 9 - row * 12,
        'text-anchor': 'middle', 'font-size': 10, fill: color, 'font-weight': 500,
      })
    );
  });
}

/** انیمیشن ورود ملایم برای شکل‌ها */
export function animateIn(node, { delay = 0 } = {}) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  node.style.opacity = '0';
  node.style.transition = `opacity .45s cubic-bezier(.22,1,.36,1) ${delay}ms`;
  requestAnimationFrame(() => {
    node.style.opacity = '1';
  });
}

/** رنگ خوانا روی پس‌زمینه رنگی (برای هیت‌مپ) */
export function contrastText(intensity) {
  return intensity > 0.55 ? 'var(--bg)' : 'var(--text)';
}

/**
 * رنگ برجسته‌سازی بر پایه معنای آن.
 * پیش‌فرض warn است چون بیشتر برجسته‌سازی‌ها «نقطه پرت» را نشان می‌دهند؛ اما وقتی
 * برجسته‌سازی به معنای «بهترین» است، رنگ هشدار پیام را وارونه می‌کند.
 */
export function highlightTone(spec) {
  const tone = spec.options?.highlightTone;
  if (tone === 'good') return 'var(--good)';
  if (tone === 'bad') return 'var(--bad)';
  if (tone === 'accent') return 'var(--accent)';
  return 'var(--warn)';
}
