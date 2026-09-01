// نمودارهای دونات، قیف، پراکندگی، راداری و هیت‌مپ

import { formatValue, fa, percent } from '../format.js';
import {
  animateIn, attachTooltip, buildScale, canvas, contrastText, el, highlightTone,
  seriesColor, text, titleTip,
} from './core.js';

/* ─────────────────── دونات ─────────────────── */
export function donutChart(spec, width) {
  const categories = spec.x.categories;
  const data = (spec.series[0]?.data || []).map(Number);
  const total = data.reduce((sum, v) => sum + (Number.isFinite(v) ? v : 0), 0);
  const format = spec.y.format || 'number';

  const size = Math.min(width, 320);
  const height = size + 16;
  const cx = width / 2;
  const cy = size / 2 + 8;
  const outer = size / 2 - 14;
  const inner = outer * 0.62;

  const svg = canvas(width, height);
  if (total <= 0) {
    svg.appendChild(
      text('داده‌ای برای نمایش وجود ندارد', { x: cx, y: cy, 'text-anchor': 'middle', 'font-size': 12 })
    );
    return svg;
  }

  const group = el('g');
  let angle = -Math.PI / 2; // شروع از بالا

  categories.forEach((label, i) => {
    const value = Number(data[i]) || 0;
    if (value <= 0) return;
    const share = value / total;
    // جهت ساعتگرد معکوس، هماهنگ با خوانش راست‌به‌چپ
    const start = angle;
    const end = angle - share * Math.PI * 2;
    angle = end;

    const large = share > 0.5 ? 1 : 0;
    const p = (radius, a) => `${cx + radius * Math.cos(a)},${cy + radius * Math.sin(a)}`;
    const color = seriesColor(i);

    const path = el('path', {
      d: `M${p(outer, start)} A${outer},${outer} 0 ${large} 0 ${p(outer, end)} L${p(inner, end)} A${inner},${inner} 0 ${large} 1 ${p(inner, start)} Z`,
      fill: color,
      stroke: 'var(--surface)',
      'stroke-width': 2.5,
      opacity: 0.94,
    });
    path.addEventListener('mouseenter', () => path.setAttribute('opacity', 1));
    path.addEventListener('mouseleave', () => path.setAttribute('opacity', 0.94));
    attachTooltip(path, label, [
      { label: fa(spec.series[0]?.name || 'مقدار'), value: formatValue(value, format), color },
      { label: 'سهم', value: percent(share) },
    ]);
    group.appendChild(path);

    // برچسب درصد داخل قوس، فقط وقتی برش به‌قدر کافی بزرگ باشد
    if (share > 0.07) {
      const mid = (start + end) / 2;
      const r = (outer + inner) / 2;
      group.appendChild(
        text(percent(share, 0), {
          x: cx + r * Math.cos(mid), y: cy + r * Math.sin(mid) + 4,
          'text-anchor': 'middle', 'font-size': 11.5, 'font-weight': 700, fill: 'var(--bg)',
        })
      );
    }
  });

  animateIn(group);
  svg.appendChild(group);

  svg.appendChild(
    text(formatValue(total, format, { compact: true }), {
      x: cx, y: cy - 2, 'text-anchor': 'middle', 'font-size': 22, 'font-weight': 700, fill: 'var(--text)',
    })
  );
  svg.appendChild(
    text('مجموع', { x: cx, y: cy + 16, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--text-faint)' })
  );
  return svg;
}

/* ─────────────────── قیف ─────────────────── */
export function funnelChart(spec, width) {
  const labels = spec.x.categories;
  const data = (spec.series[0]?.data || []).map(Number);
  const stepRates = spec.options?.stepRates || [];
  const overallRates = spec.options?.overallRates || [];
  const highlight = spec.highlight || [];

  const rowHeight = 54;
  const gap = 8;
  const height = labels.length * (rowHeight + gap) + 24;
  const maxValue = Math.max(...data.filter(Number.isFinite), 1);

  const labelWidth = Math.min(Math.max(78, width * 0.2), 140);
  const rateWidth = 84;
  const plotWidth = width - labelWidth - rateWidth - 16;
  const centerX = labelWidth + plotWidth / 2 + 8;

  const svg = canvas(width, height);
  const bottleneckColor = highlightTone({ options: { highlightTone: spec.options?.highlightTone || 'bad' } });
  const group = el('g');

  labels.forEach((label, i) => {
    const value = Number(data[i]) || 0;
    const y = 12 + i * (rowHeight + gap);
    const w = Math.max((value / maxValue) * plotWidth, 6);
    const nextValue = Number(data[i + 1]);
    const nextW = Number.isFinite(nextValue)
      ? Math.max((nextValue / maxValue) * plotWidth, 6)
      : w * 0.86;

    const isBottleneck = highlight.includes(i);
    const color = isBottleneck ? bottleneckColor : seriesColor(i);

    // ذوزنقه‌ای که پهنای بالا و پایینش با مقدار این مرحله و مرحله بعد متناسب است
    const shape = el('path', {
      d: `M${centerX - w / 2},${y} L${centerX + w / 2},${y} L${centerX + nextW / 2},${y + rowHeight} L${
        centerX - nextW / 2
      },${y + rowHeight} Z`,
      fill: color,
      opacity: isBottleneck ? 0.98 : 0.86 - i * 0.03,
      stroke: isBottleneck ? bottleneckColor : 'none',
      'stroke-width': isBottleneck ? 2 : 0,
    });

    const rows = [{ label: 'تعداد', value: formatValue(value, 'number'), color }];
    if (Number.isFinite(stepRates[i])) {
      rows.push({ label: 'عبور از مرحله قبل', value: percent(stepRates[i]) });
      rows.push({ label: 'افت', value: percent(1 - stepRates[i]) });
    }
    if (Number.isFinite(overallRates[i])) {
      rows.push({ label: 'نسبت به ورودی قیف', value: percent(overallRates[i]) });
    }
    attachTooltip(shape, label, rows);
    group.appendChild(shape);

    group.appendChild(
      text(formatValue(value, 'number'), {
        x: centerX, y: y + rowHeight / 2 + 5,
        'text-anchor': 'middle', 'font-size': 14, 'font-weight': 700, fill: 'var(--bg)',
      })
    );

    const name = text(label, {
      x: width - 8, y: y + rowHeight / 2 + 4,
      'text-anchor': 'end', 'font-size': 12.5, fill: 'var(--text)',
    });
    name.appendChild(titleTip(label));
    group.appendChild(name);

    if (Number.isFinite(stepRates[i])) {
      const rate = stepRates[i];
      group.appendChild(
        text(`${percent(rate, 0)} عبور`, {
          x: 8, y: y + rowHeight / 2 + 1,
          'text-anchor': 'start', 'font-size': 11.5, 'font-weight': 500,
          fill: isBottleneck ? bottleneckColor : 'var(--text-muted)',
        })
      );
      group.appendChild(
        text(`${percent(1 - rate, 0)} افت`, {
          x: 8, y: y + rowHeight / 2 + 15,
          'text-anchor': 'start', 'font-size': 10.5, fill: 'var(--text-faint)',
        })
      );
    }
  });

  animateIn(group);
  svg.appendChild(group);
  return svg;
}

/* ─────────────────── پراکندگی ─────────────────── */
export function scatterChart(spec, width) {
  const format = spec.y.format || 'number';
  const xFormat = spec.options?.xFormat || 'number';
  const points = spec.series.flatMap((s, si) =>
    (s.data || []).map((d) => ({ ...d, color: seriesColor(si, s.color), series: s.name }))
  );
  if (!points.length) return canvas(width, 120);

  const hasBubble = points.some((p) => Number.isFinite(p.r));
  const identity = Boolean(spec.options?.identityLine);

  const xs = points.map((p) => Number(p.x));
  const ys = points.map((p) => Number(p.y));
  let xScale = buildScale(xs, { includeZero: false, targetTicks: 5, padTop: 0.1 });
  let yScale = buildScale(ys, { includeZero: false, targetTicks: 5, padTop: 0.1 });
  if (identity) {
    // برای مقایسه واقعی و پیش‌بینی، هر دو محور باید دامنه یکسان داشته باشند
    const all = xs.concat(ys);
    xScale = yScale = buildScale(all, { includeZero: false, targetTicks: 5, padTop: 0.08 });
  }

  // برچسب محور عمودی سمت راست رسم می‌شود، پس فضای بیشتری در right لازم است
  const pad = { top: 18, right: 56, bottom: 46, left: 22 };
  const height = 330;
  const plot = {
    x: pad.left, y: pad.top,
    w: width - pad.left - pad.right,
    h: height - pad.top - pad.bottom,
  };

  const svg = canvas(width, height);
  const toX = (v) => plot.x + plot.w - ((v - xScale.min) / (xScale.max - xScale.min)) * plot.w;
  const toY = (v) => plot.y + plot.h - ((v - yScale.min) / (yScale.max - yScale.min)) * plot.h;

  yScale.ticks.forEach((tick) => {
    const y = toY(tick);
    svg.appendChild(
      el('line', { x1: plot.x, x2: plot.x + plot.w, y1: y, y2: y, stroke: 'var(--grid)', 'stroke-width': 1 })
    );
    svg.appendChild(
      text(formatValue(tick, format, { compact: true }), {
        x: plot.x + plot.w + 8, y: y + 3.5, 'text-anchor': 'start', 'font-size': 10.5, fill: 'var(--text-faint)',
      })
    );
  });
  xScale.ticks.forEach((tick) => {
    const x = toX(tick);
    svg.appendChild(
      el('line', { x1: x, x2: x, y1: plot.y, y2: plot.y + plot.h, stroke: 'var(--grid)', 'stroke-width': 1 })
    );
    svg.appendChild(
      text(formatValue(tick, xFormat, { compact: true }), {
        x, y: plot.y + plot.h + 16, 'text-anchor': 'middle', 'font-size': 10.5, fill: 'var(--text-faint)',
      })
    );
  });

  if (identity) {
    const lo = Math.max(xScale.min, yScale.min);
    const hi = Math.min(xScale.max, yScale.max);
    svg.appendChild(
      el('line', {
        x1: toX(lo), y1: toY(lo), x2: toX(hi), y2: toY(hi),
        stroke: 'var(--text-faint)', 'stroke-width': 1.3, 'stroke-dasharray': '5 4', opacity: 0.75,
      })
    );
  }

  if (spec.x.label) {
    svg.appendChild(
      text(spec.x.label, {
        x: plot.x + plot.w / 2, y: height - 8, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--text-muted)',
      })
    );
  }

  const radii = points.map((p) => Number(p.r)).filter(Number.isFinite);
  const rMin = radii.length ? Math.min(...radii) : 0;
  const rMax = radii.length ? Math.max(...radii) : 1;
  const radiusOf = (p) => {
    if (!hasBubble || !Number.isFinite(p.r)) return spec.options?.pointRadius || 4;
    if (rMax === rMin) return 15;
    // مساحت (نه شعاع) متناسب با مقدار است تا اندازه حباب گمراه‌کننده نباشد
    const t = (Number(p.r) - rMin) / (rMax - rMin);
    return Math.sqrt(49 + t * (576 - 49));
  };

  const group = el('g');
  const labels = el('g');

  points.forEach((p) => {
    const x = toX(Number(p.x));
    const y = toY(Number(p.y));
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    const r = radiusOf(p);

    const dot = el('circle', {
      cx: x, cy: y, r,
      fill: p.color,
      opacity: hasBubble ? 0.42 : 0.66,
      stroke: p.color,
      'stroke-width': hasBubble ? 1.8 : 1,
    });
    const rows = [
      { label: spec.x.label || 'x', value: formatValue(p.x, xFormat) },
      { label: spec.y.label || 'y', value: formatValue(p.y, format) },
    ];
    if (Number.isFinite(p.r)) {
      rows.push({
        label: spec.options?.bubbleLabel || 'اندازه',
        value: formatValue(p.r, spec.options?.bubbleFormat || 'number'),
      });
    }
    attachTooltip(dot, p.label || p.series, rows);
    group.appendChild(dot);

    if (hasBubble && p.label) {
      // برچسب زیر حباب می‌نشیند و هاله‌ای هم‌رنگ پس‌زمینه دارد تا در حباب‌های
      // روی‌هم‌افتاده هم خوانا بماند
      const node = text(p.label, {
        x, y: y + r + 13, 'text-anchor': 'middle', 'font-size': 11.5, 'font-weight': 500,
        fill: 'var(--text)', 'pointer-events': 'none',
        stroke: 'var(--surface)', 'stroke-width': 3.5, 'paint-order': 'stroke',
      });
      labels.appendChild(node);
    }
  });

  animateIn(group);
  svg.appendChild(group);
  svg.appendChild(labels);
  return svg;
}

/* ─────────────────── راداری ─────────────────── */
export function radarChart(spec, width) {
  const axes = spec.x.categories;
  const count = axes.length;
  if (!count) return canvas(width, 120);

  const size = Math.min(width, 380);
  const height = size + 10;
  const cx = width / 2;
  const cy = size / 2 + 4;
  const radius = size / 2 - 58;

  const svg = canvas(width, height);
  const angleOf = (i) => -Math.PI / 2 - (i / count) * Math.PI * 2; // راست‌گرد معکوس
  const point = (i, t) => ({
    x: cx + radius * t * Math.cos(angleOf(i)),
    y: cy + radius * t * Math.sin(angleOf(i)),
  });

  [0.25, 0.5, 0.75, 1].forEach((t) => {
    const ring = Array.from({ length: count }, (_, i) => point(i, t));
    svg.appendChild(
      el('polygon', {
        points: ring.map((p) => `${p.x},${p.y}`).join(' '),
        fill: 'none', stroke: 'var(--grid)', 'stroke-width': 1,
      })
    );
  });

  axes.forEach((label, i) => {
    const outer = point(i, 1);
    svg.appendChild(
      el('line', { x1: cx, y1: cy, x2: outer.x, y2: outer.y, stroke: 'var(--grid)', 'stroke-width': 1 })
    );
    const labelPoint = point(i, 1.17);
    const anchor =
      Math.abs(labelPoint.x - cx) < 12 ? 'middle' : labelPoint.x > cx ? 'start' : 'end';
    const node = text(label, {
      x: labelPoint.x, y: labelPoint.y + 4, 'text-anchor': anchor, 'font-size': 11, fill: 'var(--text-muted)',
    });
    node.appendChild(titleTip(label));
    svg.appendChild(node);
  });

  const group = el('g');
  spec.series.forEach((series, si) => {
    const color = seriesColor(si, series.color);
    const points = series.data.map((raw, i) => {
      const value = Math.max(0, Math.min(1, Number(raw) || 0));
      return { ...point(i, value), value, axis: axes[i] };
    });

    const polygon = el('polygon', {
      points: points.map((p) => `${p.x},${p.y}`).join(' '),
      fill: color, 'fill-opacity': 0.14, stroke: color, 'stroke-width': 2.2, 'stroke-linejoin': 'round',
    });
    attachTooltip(
      polygon,
      series.name,
      points.map((p) => ({ label: fa(p.axis), value: formatValue(p.value, 'number'), color }))
    );
    group.appendChild(polygon);

    points.forEach((p) => {
      group.appendChild(
        el('circle', { cx: p.x, cy: p.y, r: 3.2, fill: color, stroke: 'var(--surface)', 'stroke-width': 1.5 })
      );
    });
  });

  animateIn(group);
  svg.appendChild(group);
  svg.__toggleSeries = (index, on) => {
    const child = group.children[index * 1];
    if (child) child.style.display = on ? '' : 'none';
  };
  return svg;
}

/* ─────────────────── هیت‌مپ ─────────────────── */
export function heatmapChart(spec, width) {
  const cols = spec.x.categories;
  const rows = spec.options?.rows || spec.series.map((s) => s.name);
  const format = spec.y.format || 'percent';

  const values = spec.series.flatMap((s) => s.data.map(Number)).filter(Number.isFinite);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);

  const longestRow = rows.reduce((m, r) => Math.max(m, String(r).length), 0);
  const labelWidth = Math.min(Math.max(84, longestRow * 7.2), width * 0.3);
  const topSpace = 42;
  const cellHeight = 42;
  const gap = 4;

  const gridWidth = width - labelWidth - 12;
  const cellWidth = gridWidth / Math.max(cols.length, 1);
  const height = topSpace + rows.length * (cellHeight + gap) + 8;

  const svg = canvas(width, height);

  cols.forEach((col, ci) => {
    // راست به چپ
    const cx = 8 + gridWidth - (ci + 0.5) * cellWidth;
    const node = text(col, {
      x: cx, y: topSpace - 12, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--text-muted)',
    });
    node.appendChild(titleTip(col));
    svg.appendChild(node);
  });

  const group = el('g');
  rows.forEach((row, ri) => {
    const y = topSpace + ri * (cellHeight + gap);
    const label = text(row, {
      x: width - 8, y: y + cellHeight / 2 + 4, 'text-anchor': 'end', 'font-size': 12, fill: 'var(--text)',
    });
    label.appendChild(titleTip(row));
    group.appendChild(label);

    const data = spec.series[ri]?.data || [];
    cols.forEach((col, ci) => {
      const value = Number(data[ci]);
      const x = 8 + gridWidth - (ci + 1) * cellWidth;
      if (!Number.isFinite(value)) return;

      const t = max === min ? 0.5 : (value - min) / (max - min);
      const cell = el('rect', {
        x: x + 2, y, width: cellWidth - 4, height: cellHeight, rx: 6,
        fill: 'var(--accent)',
        // کف ۰٫۱ تا خانه‌های کم‌مقدار هم دیده شوند
        'fill-opacity': 0.1 + t * 0.85,
      });
      attachTooltip(cell, `${row} · ${col}`, [
        { label: spec.y.label || 'مقدار', value: formatValue(value, format), color: 'var(--accent)' },
      ]);
      group.appendChild(cell);

      group.appendChild(
        text(formatValue(value, format, { compact: true }), {
          x: x + cellWidth / 2, y: y + cellHeight / 2 + 4,
          'text-anchor': 'middle', 'font-size': 11.5, 'font-weight': 500,
          fill: contrastText(t), 'pointer-events': 'none',
        })
      );
    });
  });

  animateIn(group);
  svg.appendChild(group);
  return svg;
}
