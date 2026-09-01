// نمودار ستونی: ساده، گروهی، انباشته، هیستوگرام، ستونی افقی و میله اختلاف

import { formatValue, fa } from '../format.js';
import {
  animateIn, attachTooltip, buildScale, canvas, drawAnnotations, drawAnnotationsX,
  el, highlightTone, seriesColor, text, titleTip, xAxisLabels, xLabelSpace, yAxis,
} from './core.js';

// در چیدمان راست‌به‌چپ، برچسب محور مقدار سمت راست رسم می‌شود، پس فضای اصلی در right رزرو می‌شود.
// left فقط وقتی نیاز است که نمودار محور دوم داشته باشد.
const PAD = { top: 18, right: 52, bottom: 8, left: 16 };
const AXIS_SPACE = 52;

/** ستونی عمودی — تکی، گروهی، انباشته، هیستوگرام و ترکیب ستون با خط */
export function barChart(spec, width) {
  const categories = spec.x.categories;
  const stacked = Boolean(spec.stacked);
  const isHistogram = spec.type === 'histogram';
  const format = spec.y.format || 'number';

  const bars = spec.series.filter((s) => s.kind !== 'line');
  const lines = spec.series.filter((s) => s.kind === 'line');
  // محور دوم فقط وقتی معنا دارد که سری خطی با مقیاسی کاملاً متفاوت وجود داشته باشد
  const dualAxis = Boolean(spec.options?.dualAxis) && lines.length > 0;

  const barValues = stacked
    ? categories.map((_, i) => bars.reduce((sum, s) => sum + (Number(s.data[i]) || 0), 0))
    : bars.flatMap((s) => s.data.map(Number));
  const scaleValues = dualAxis ? barValues : barValues.concat(lines.flatMap((s) => s.data.map(Number)));
  const scale = buildScale(scaleValues.concat((spec.annotations || []).map((a) => a.value)));

  const leftPad = dualAxis ? AXIS_SPACE : PAD.left;
  const bandCount = Math.max(categories.length, 1);
  const provisionalBand = (width - leftPad - PAD.right) / bandCount;
  const bottomSpace = xLabelSpace(categories, provisionalBand);

  const height = Math.max(250, Math.min(400, 210 + bandCount * 4)) + bottomSpace;
  const plot = {
    x: leftPad,
    y: PAD.top,
    w: width - leftPad - PAD.right,
    h: height - PAD.top - PAD.bottom - bottomSpace,
  };
  const band = plot.w / bandCount;

  const svg = canvas(width, height);
  const highlightColor = highlightTone(spec);
  const { group: grid, toY } = yAxis(scale, plot, format);
  svg.appendChild(grid);

  const groupCount = stacked ? 1 : bars.length || 1;
  const gapRatio = isHistogram ? 0.06 : 0.3;
  // سقف پهنا تا در نمودارهای کم‌دسته، ستون‌ها بیش از حد پهن و نامتناسب نشوند
  const maxBarWidth = isHistogram ? Infinity : 78 / groupCount;
  const barWidth = Math.max(3, Math.min((band * (1 - gapRatio)) / groupCount, maxBarWidth));

  bars.forEach((series, si) => {
    const seriesGroup = el('g');
    const color = seriesColor(si, series.color);
    const stackBase = new Array(categories.length).fill(0);

    categories.forEach((label, ci) => {
      const value = Number(series.data[ci]);
      if (!Number.isFinite(value)) return;

      // راست به چپ: اولین دسته در سمت راست قرار می‌گیرد
      const bandStart = plot.x + plot.w - (ci + 1) * band;
      const offset = stacked
        ? (band - barWidth) / 2
        : (band - barWidth * groupCount) / 2 + (groupCount - 1 - si) * barWidth;
      const x = bandStart + offset;

      let y0 = toY(0);
      let y1 = toY(value);
      if (stacked) {
        const prev = bars.slice(0, si).reduce((sum, s) => sum + (Number(s.data[ci]) || 0), 0);
        y0 = toY(prev);
        y1 = toY(prev + value);
      }

      const top = Math.min(y0, y1);
      const barHeight = Math.max(Math.abs(y1 - y0), value === 0 ? 0 : 1.5);
      const highlighted = (spec.highlight || []).includes(ci);

      const rect = el('rect', {
        x, y: top, width: barWidth, height: barHeight,
        rx: Math.min(4, barWidth / 2.6),
        fill: highlighted ? highlightColor : color,
        opacity: highlighted ? 1 : 0.92,
      });
      if (highlighted) {
        rect.setAttribute('stroke', highlightColor);
        rect.setAttribute('stroke-width', 1.5);
      }
      attachTooltip(rect, label, [
        { label: fa(series.name), value: formatValue(value, format), color },
      ]);
      seriesGroup.appendChild(rect);
    });

    animateIn(seriesGroup, { delay: si * 60 });
    svg.appendChild(seriesGroup);
  });

  // سری خطی روی ستون‌ها (مثلاً سرانه هزینه روی هزینه کل)
  if (lines.length) {
    const lineScale = dualAxis
      ? buildScale(lines.flatMap((s) => s.data.map(Number)))
      : scale;
    const toY2 = (v) =>
      plot.y + plot.h - ((v - lineScale.min) / (lineScale.max - lineScale.min)) * plot.h;

    if (dualAxis) {
      lineScale.ticks.forEach((tick) => {
        svg.appendChild(
          text(formatValue(tick, format, { compact: true }), {
            x: plot.x - 8, y: toY2(tick) + 3.5, 'text-anchor': 'end',
            'font-size': 10.5, fill: 'var(--text-faint)',
          })
        );
      });
    }

    lines.forEach((series, li) => {
      const color = seriesColor(bars.length + li, series.color);
      const points = categories
        .map((label, ci) => {
          const value = Number(series.data[ci]);
          if (!Number.isFinite(value)) return null;
          return { x: plot.x + plot.w - (ci + 0.5) * band, y: toY2(value), value, label };
        })
        .filter(Boolean);

      if (points.length > 1) {
        svg.appendChild(
          el('polyline', {
            points: points.map((p) => `${p.x},${p.y}`).join(' '),
            fill: 'none', stroke: color, 'stroke-width': 2.4,
            'stroke-linejoin': 'round', 'stroke-linecap': 'round',
          })
        );
      }
      points.forEach((p) => {
        const dot = el('circle', {
          cx: p.x, cy: p.y, r: 4, fill: color, stroke: 'var(--surface)', 'stroke-width': 2,
        });
        attachTooltip(dot, p.label, [
          { label: fa(series.name), value: formatValue(p.value, format), color },
        ]);
        svg.appendChild(dot);
      });
    });
  }

  drawAnnotations(svg, spec.annotations, plot, toY, format);
  svg.appendChild(xAxisLabels(categories, plot, band).group);
  return svg;
}

/** ستونی افقی — برای مقایسه گروه‌های با نام بلند */
export function hbarChart(spec, width) {
  const categories = spec.x.categories;
  const series = spec.series[0];
  if (!series) return canvas(width, 80);
  const format = spec.y.format || 'number';

  const values = series.data.map(Number);
  const scale = buildScale(values.concat((spec.annotations || []).map((a) => a.value)), {
    targetTicks: 5, padTop: 0.05,
  });

  // پهنای ستون نام‌ها بر پایه بلندترین برچسب (سقف: یک‌سوم عرض نمودار)
  const longest = categories.reduce((m, c) => Math.max(m, String(c).length), 0);
  const labelWidth = Math.min(Math.max(78, longest * 7.4), width * 0.34);

  const rowHeight = 34;
  // برچسب آستانه‌ها ممکن است روی دو سطر بنشیند، پس فضای بالا با تعدادشان تنظیم می‌شود
  const annotationCount = (spec.annotations || []).length;
  const topPad = annotationCount > 1 ? 40 : annotationCount ? 26 : 14;
  const height = topPad + categories.length * rowHeight + 26;
  const plot = { x: 16, y: topPad, w: width - labelWidth - 22, h: categories.length * rowHeight };

  const svg = canvas(width, height);
  const highlightColor = highlightTone(spec);
  const toX = (v) => plot.x + plot.w - ((v - scale.min) / (scale.max - scale.min)) * plot.w;

  scale.ticks.forEach((tick) => {
    const x = toX(tick);
    svg.appendChild(
      el('line', {
        x1: x, x2: x, y1: plot.y, y2: plot.y + plot.h,
        stroke: 'var(--grid)', 'stroke-width': 1,
      })
    );
    svg.appendChild(
      text(formatValue(tick, format, { compact: true }), {
        x, y: plot.y + plot.h + 16, 'text-anchor': 'middle', 'font-size': 10.5, fill: 'var(--text-faint)',
      })
    );
  });

  const group = el('g');
  categories.forEach((label, i) => {
    const value = Number(series.data[i]);
    const cy = plot.y + i * rowHeight + rowHeight / 2;

    const name = text(label, {
      x: width - 14, y: cy + 4, 'text-anchor': 'end', 'font-size': 12, fill: 'var(--text)',
    });
    name.appendChild(titleTip(label));
    group.appendChild(name);

    if (!Number.isFinite(value)) return;
    const zeroX = toX(Math.max(scale.min, 0));
    const valueX = toX(value);
    const highlighted = (spec.highlight || []).includes(i);
    const color = highlighted ? highlightColor : seriesColor(0, series.color);

    const rect = el('rect', {
      x: Math.min(zeroX, valueX), y: cy - 9,
      width: Math.max(Math.abs(valueX - zeroX), 2), height: 18,
      rx: 4, fill: color, opacity: highlighted ? 1 : 0.9,
    });
    attachTooltip(rect, label, [{ label: fa(series.name), value: formatValue(value, format), color }]);
    group.appendChild(rect);

    // برچسب مقدار همیشه در همان سمتی می‌نشیند که میله به آن رشد کرده است.
    // در چیدمان راست‌به‌چپ، مقدار مثبت به چپ و مقدار منفی به راست کشیده می‌شود.
    const barLength = Math.abs(valueX - zeroX);
    const inside = barLength > 58;
    const growsLeft = valueX <= zeroX;
    group.appendChild(
      text(formatValue(value, format, { compact: true }), {
        x: inside === growsLeft ? valueX + 8 : valueX - 8,
        y: cy + 4,
        'text-anchor': inside === growsLeft ? 'start' : 'end',
        'font-size': 11,
        'font-weight': 500,
        fill: inside ? 'var(--bg)' : 'var(--text-muted)',
      })
    );
  });

  animateIn(group);
  svg.appendChild(group);
  drawAnnotationsX(svg, spec.annotations, plot, toX);
  return svg;
}

/** میله اختلاف دوطرفه حول خط صفر */
export function diffBarChart(spec, width) {
  const categories = spec.x.categories;
  const series = spec.series[0];
  if (!series) return canvas(width, 80);
  const format = spec.y.format || 'percent';

  const values = series.data.map(Number).filter(Number.isFinite);
  const extent = Math.max(...values.map(Math.abs), 0.001) * 1.18;

  const longest = categories.reduce((m, c) => Math.max(m, String(c).length), 0);
  const labelWidth = Math.min(Math.max(90, longest * 7.4), width * 0.36);
  const rowHeight = 32;
  const height = 24 + categories.length * rowHeight + 24;
  const plot = { x: 16, y: 20, w: width - labelWidth - 22, h: categories.length * rowHeight };
  const centerX = plot.x + plot.w / 2;

  const svg = canvas(width, height);
  const toX = (v) => centerX - (v / extent) * (plot.w / 2);

  svg.appendChild(
    el('line', {
      x1: centerX, x2: centerX, y1: plot.y - 6, y2: plot.y + plot.h,
      stroke: 'var(--axis)', 'stroke-width': 1.2,
    })
  );
  svg.appendChild(
    text('بدون اختلاف', {
      x: centerX, y: plot.y - 10, 'text-anchor': 'middle', 'font-size': 10, fill: 'var(--text-faint)',
    })
  );

  const group = el('g');
  categories.forEach((label, i) => {
    const value = Number(series.data[i]);
    const cy = plot.y + i * rowHeight + rowHeight / 2;

    const name = text(label, {
      x: width - 14, y: cy + 4, 'text-anchor': 'end', 'font-size': 12, fill: 'var(--text)',
    });
    name.appendChild(titleTip(label));
    group.appendChild(name);

    if (!Number.isFinite(value)) return;
    const x = toX(value);
    // مثبت یعنی گروه ترک‌کرده بالاتر بوده است — با رنگ هشدار
    const color = value >= 0 ? 'var(--bad)' : 'var(--good)';

    const rect = el('rect', {
      x: Math.min(centerX, x), y: cy - 8,
      width: Math.max(Math.abs(x - centerX), 2), height: 16,
      rx: 4, fill: color, opacity: 0.88,
    });
    attachTooltip(rect, label, [{ label: fa(series.name), value: formatValue(value, format), color }]);
    group.appendChild(rect);

    group.appendChild(
      text(formatValue(value, format), {
        x: value >= 0 ? Math.min(centerX, x) - 7 : Math.max(centerX, x) + 7,
        y: cy + 4,
        'text-anchor': value >= 0 ? 'end' : 'start',
        'font-size': 10.5, fill: 'var(--text-muted)',
      })
    );
  });

  animateIn(group);
  svg.appendChild(group);
  return svg;
}
