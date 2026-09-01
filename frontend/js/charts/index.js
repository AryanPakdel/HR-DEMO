// رندرکننده عمومی نمودار: از روی spec بک‌اند نوع مناسب را انتخاب و رسم می‌کند

import { fa } from '../format.js';
import { icon } from '../icons.js';
import { barChart, diffBarChart, hbarChart } from './bar.js';
import { areaChart, lineChart } from './line.js';
import { renderLegend } from './core.js';
import { donutChart, funnelChart, heatmapChart, radarChart, scatterChart } from './parts.js';

const RENDERERS = {
  bar: barChart,
  histogram: barChart,
  hbar: hbarChart,
  diffbar: diffBarChart,
  line: lineChart,
  area: areaChart,
  donut: donutChart,
  funnel: funnelChart,
  scatter: scatterChart,
  radar: radarChart,
  heatmap: heatmapChart,
};

// نمودارهایی که خودشان برچسب دسته را کنار شکل می‌نویسند و به لجند نیاز ندارند
const SELF_LABELED = new Set(['hbar', 'diffbar', 'funnel', 'heatmap']);

function svgToPng(svg, filename) {
  const clone = svg.cloneNode(true);
  const box = svg.viewBox.baseVal;
  const width = box.width || svg.clientWidth || 800;
  const height = box.height || 400;
  const scale = 2;

  // متغیرهای CSS داخل رشته SVG معنا ندارند، پس با مقدار محاسبه‌شده جایگزین می‌شوند
  const computed = getComputedStyle(document.documentElement);
  const resolve = (value) =>
    String(value).replace(/var\((--[a-z0-9-]+)\)/gi, (_, name) => computed.getPropertyValue(name).trim() || '#888');

  clone.querySelectorAll('*').forEach((node) => {
    ['fill', 'stroke', 'color'].forEach((attr) => {
      const value = node.getAttribute(attr);
      if (value && value.includes('var(')) node.setAttribute(attr, resolve(value));
    });
  });
  clone.setAttribute('width', width);
  clone.setAttribute('height', height);
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

  const background = computed.getPropertyValue('--surface').trim() || '#fff';
  const source = new XMLSerializer().serializeToString(clone);
  const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(source)}`;

  const image = new Image();
  image.onload = () => {
    const canvasEl = document.createElement('canvas');
    canvasEl.width = width * scale;
    canvasEl.height = height * scale;
    const ctx = canvasEl.getContext('2d');
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, canvasEl.width, canvasEl.height);
    ctx.drawImage(image, 0, 0, canvasEl.width, canvasEl.height);
    canvasEl.toBlob((blob) => {
      if (!blob) return;
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    });
  };
  image.onerror = () => {
    // اگر تبدیل به تصویر ممکن نبود، خود SVG دانلود می‌شود
    const link = document.createElement('a');
    link.href = url;
    link.download = filename.replace(/\.png$/, '.svg');
    link.click();
  };
  image.src = url;
}

/** ساخت کارت کامل یک نمودار از روی spec */
export function renderChart(spec) {
  const card = document.createElement('div');
  card.className = 'chart';

  const head = document.createElement('div');
  head.className = 'chart__head';
  head.innerHTML = `
    <div>
      <div class="chart__title">${fa(spec.title)}</div>
      ${spec.subtitle ? `<div class="chart__subtitle">${fa(spec.subtitle)}</div>` : ''}
    </div>`;

  const exportBtn = document.createElement('button');
  exportBtn.className = 'icon-btn chart__export';
  exportBtn.type = 'button';
  exportBtn.title = 'دانلود تصویر نمودار';
  exportBtn.setAttribute('aria-label', 'دانلود تصویر نمودار');
  exportBtn.innerHTML = icon('download');
  head.appendChild(exportBtn);
  card.appendChild(head);

  const body = document.createElement('div');
  body.className = 'chart__body';
  card.appendChild(body);

  if (spec.footnote) {
    const foot = document.createElement('div');
    foot.className = 'chart__foot';
    foot.textContent = fa(spec.footnote);
    card.appendChild(foot);
  }

  const renderer = RENDERERS[spec.type] || barChart;
  let svg = null;

  // نمودار با عرض واقعی کارت رسم و در تغییر اندازه پنجره بازرسم می‌شود
  const draw = () => {
    const width = Math.max(280, Math.round(body.clientWidth || card.clientWidth || 640));
    body.textContent = '';
    const legendNode = card.querySelector('.legend');
    if (legendNode) legendNode.remove();

    svg = renderer(spec, width);
    body.appendChild(svg);

    if (!SELF_LABELED.has(spec.type) && spec.series.length > 1) {
      renderLegend(card, spec.series, {
        onToggle: svg.__toggleSeries ? (i, on) => svg.__toggleSeries(i, on) : undefined,
      });
    }
  };

  exportBtn.addEventListener('click', () => {
    if (svg) svgToPng(svg, `${spec.title.slice(0, 40) || 'chart'}.png`);
  });

  // ResizeObserver تا نمودار با تغییر عرض کارت (نه فقط پنجره) هم بازرسم شود
  let lastWidth = 0;
  const observer = new ResizeObserver(() => {
    const width = Math.round(body.clientWidth);
    if (width && Math.abs(width - lastWidth) > 12) {
      lastWidth = width;
      draw();
    }
  });
  requestAnimationFrame(() => {
    draw();
    lastWidth = Math.round(body.clientWidth);
    observer.observe(body);
  });

  card.__cleanup = () => observer.disconnect();
  return card;
}
