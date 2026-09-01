// نمودار خطی و سطحی با تعامل نشانگر عمودی

import { formatValue, fa } from '../format.js';
import {
  animateIn, buildScale, canvas, drawAnnotations, el, hideTooltip, seriesColor,
  showTooltip, text, tooltipHtml, xAxisLabels, xLabelSpace, yAxis,
} from './core.js';

// راست‌به‌چپ: برچسب محور مقدار سمت راست قرار می‌گیرد
const PAD = { top: 18, right: 52, bottom: 8, left: 16 };

export function lineChart(spec, width, { area = false } = {}) {
  const categories = spec.x.categories;
  const format = spec.y.format || 'number';
  const visible = spec.series.map(() => true);

  const values = spec.series.flatMap((s) => s.data.map(Number));
  const scale = buildScale(values.concat((spec.annotations || []).map((a) => a.value)), {
    includeZero: area, padTop: 0.1,
  });

  // در سری‌های زمانی بلند فقط بخشی از برچسب‌ها نمایش داده می‌شود
  const step = Math.max(1, Math.ceil(categories.length / 12));
  const shown = categories.map((c, i) => (i % step === 0 ? c : ''));
  const provisionalBand = (width - PAD.left - PAD.right) / Math.max(categories.length, 1);
  const bottomSpace = xLabelSpace(shown.filter(Boolean), provisionalBand * step);

  const height = 300 + bottomSpace - 26;
  const plot = {
    x: PAD.left, y: PAD.top,
    w: width - PAD.left - PAD.right,
    h: height - PAD.top - PAD.bottom - bottomSpace,
  };

  const svg = canvas(width, height);
  const { group: grid, toY } = yAxis(scale, plot, format);
  svg.appendChild(grid);

  const count = Math.max(categories.length - 1, 1);
  // راست به چپ: نقطه صفر در سمت راست
  const toX = (i) =>
    categories.length === 1 ? plot.x + plot.w / 2 : plot.x + plot.w - (i / count) * plot.w;

  const layers = [];
  spec.series.forEach((series, si) => {
    const color = seriesColor(si, series.color);
    const layer = el('g');
    const points = series.data
      .map((raw, i) => {
        const value = Number(raw);
        return Number.isFinite(value) ? { x: toX(i), y: toY(value), value, i } : null;
      })
      .filter(Boolean);
    if (!points.length) {
      layers.push(layer);
      svg.appendChild(layer);
      return;
    }

    if (area) {
      const baseY = toY(Math.max(scale.min, 0));
      const gradientId = `grad-${Math.random().toString(36).slice(2, 9)}`;
      const defs = el('defs');
      const gradient = el('linearGradient', { id: gradientId, x1: 0, y1: 0, x2: 0, y2: 1 });
      gradient.appendChild(el('stop', { offset: '0%', 'stop-color': color, 'stop-opacity': 0.36 }));
      gradient.appendChild(el('stop', { offset: '100%', 'stop-color': color, 'stop-opacity': 0.02 }));
      defs.appendChild(gradient);
      layer.appendChild(defs);
      layer.appendChild(
        el('path', {
          d: `M${points[0].x},${baseY} ${points.map((p) => `L${p.x},${p.y}`).join(' ')} L${
            points[points.length - 1].x
          },${baseY} Z`,
          fill: `url(#${gradientId})`,
        })
      );
    }

    layer.appendChild(
      el('polyline', {
        points: points.map((p) => `${p.x},${p.y}`).join(' '),
        fill: 'none', stroke: color, 'stroke-width': 2.4,
        'stroke-linejoin': 'round', 'stroke-linecap': 'round',
      })
    );

    // در سری‌های کوتاه هر نقطه نشان داده می‌شود
    if (points.length <= 20) {
      points.forEach((p) => {
        layer.appendChild(
          el('circle', { cx: p.x, cy: p.y, r: 3.2, fill: color, stroke: 'var(--surface)', 'stroke-width': 1.6 })
        );
      });
    }

    animateIn(layer, { delay: si * 70 });
    layers.push(layer);
    svg.appendChild(layer);
  });

  drawAnnotations(svg, spec.annotations, plot, toY, format);
  svg.appendChild(xAxisLabels(shown, plot, plot.w / Math.max(categories.length, 1)).group);

  // نشانگر عمودی که نزدیک‌ترین نقطه را دنبال می‌کند
  const marker = el('line', {
    y1: plot.y, y2: plot.y + plot.h, stroke: 'var(--border-strong)', 'stroke-width': 1,
    'stroke-dasharray': '3 3', opacity: 0,
  });
  svg.appendChild(marker);
  const dots = el('g');
  svg.appendChild(dots);

  const overlay = el('rect', {
    x: plot.x, y: plot.y, width: plot.w, height: plot.h, fill: 'transparent',
  });
  overlay.style.cursor = 'crosshair';
  svg.appendChild(overlay);

  const pointerIndex = (event) => {
    const rect = svg.getBoundingClientRect();
    const relative = ((event.clientX - rect.left) / rect.width) * width;
    const ratio = (plot.x + plot.w - relative) / plot.w;
    return Math.max(0, Math.min(categories.length - 1, Math.round(ratio * count)));
  };

  overlay.addEventListener('mousemove', (event) => {
    const i = pointerIndex(event);
    const x = toX(i);
    marker.setAttribute('x1', x);
    marker.setAttribute('x2', x);
    marker.setAttribute('opacity', 1);

    dots.textContent = '';
    const rows = [];
    spec.series.forEach((series, si) => {
      if (!visible[si]) return;
      const value = Number(series.data[i]);
      if (!Number.isFinite(value)) return;
      const color = seriesColor(si, series.color);
      dots.appendChild(
        el('circle', { cx: x, cy: toY(value), r: 5, fill: color, stroke: 'var(--surface)', 'stroke-width': 2 })
      );
      rows.push({ label: fa(series.name), value: formatValue(value, format), color });
    });
    if (rows.length) showTooltip(event, tooltipHtml(categories[i], rows));
  });

  overlay.addEventListener('mouseleave', () => {
    marker.setAttribute('opacity', 0);
    dots.textContent = '';
    hideTooltip();
  });

  svg.__toggleSeries = (index, on) => {
    visible[index] = on;
    layers[index].style.display = on ? '' : 'none';
  };
  return svg;
}

export function areaChart(spec, width) {
  return lineChart(spec, width, { area: true });
}
