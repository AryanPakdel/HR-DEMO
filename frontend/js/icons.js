// آیکون‌های SVG درون‌خطی — بدون وابستگی خارجی، آفلاین‌پذیر

const P = (d, extra = '') =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}${extra}</svg>`;

export const icons = {
  logo: P('<path d="M3 17l5-5 4 3 6-7"/><circle cx="18" cy="8" r="1.6" fill="currentColor" stroke="none"/>'),
  upload: P('<path d="M12 16V4"/><path d="M8 8l4-4 4 4"/><path d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2"/>'),
  file: P('<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z"/><path d="M14 3v5h5"/>'),
  check: P('<path d="M20 6L9 17l-5-5"/>'),
  alert: P('<circle cx="12" cy="12" r="9"/><path d="M12 8v5"/><path d="M12 16.5v.01"/>'),
  info: P('<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 7.5v.01"/>'),
  good: P('<circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/>'),
  search: P('<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>'),
  arrowLeft: P('<path d="M19 12H5"/><path d="M11 18l-6-6 6-6"/>'),
  arrowRight: P('<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>'),
  chevron: P('<path d="M15 6l-6 6 6 6"/>'),
  home: P('<path d="M3 10l9-7 9 7v9a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><path d="M9 21v-8h6v8"/>'),
  sun: P('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
  moon: P('<path d="M20 14.5A8.5 8.5 0 019.5 4a8.5 8.5 0 1010.5 10.5z"/>'),
  download: P('<path d="M12 4v11"/><path d="M8 11l4 4 4-4"/><path d="M4 19h16"/>'),
  refresh: P('<path d="M20 11a8 8 0 10-1.6 5.6"/><path d="M20 4v6h-6"/>'),
  reset: P('<path d="M4 13a8 8 0 101.6-5.6"/><path d="M4 4v6h6"/>'),
  // آیکون سؤالات
  trend: P('<path d="M3 17l5.5-5.5 3.5 3.5L21 6"/><path d="M15 6h6v6"/>'),
  layers: P('<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>'),
  clock: P('<circle cx="12" cy="12" r="9"/><path d="M12 7v5.5l3.5 2"/>'),
  funnel: P('<path d="M3 4h18l-7 8v7l-4 2v-9z"/>'),
  cost: P('<circle cx="12" cy="12" r="9"/><path d="M14.5 9.2A2.6 2.6 0 0012 8c-1.5 0-2.6.9-2.6 2s1.1 2 2.6 2 2.6.9 2.6 2-1.1 2-2.6 2a2.6 2.6 0 01-2.5-1.2"/><path d="M12 6.5v11"/>'),
  channel: P('<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M7.6 8L11 15.6M16.4 8L13 15.6"/>'),
  handshake: P('<path d="M8 12l2.5 2.5a1.6 1.6 0 002.3 0L18 9.4"/><path d="M3 9l4-4 4 3"/><path d="M21 9l-4-4-3 2"/><path d="M3 9v5l4 4"/><path d="M21 9v5l-3 3"/>'),
  quality: P('<path d="M12 3l2.6 5.5 6 .9-4.3 4.2 1 6-5.3-2.9-5.3 2.9 1-6L3.4 9.4l6-.9z"/>'),
  search2: P('<circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.8-4.8"/><path d="M10.5 7.5v6M7.5 10.5h6"/>'),
  bottleneck: P('<path d="M5 3h14"/><path d="M5 3l5.5 7v4.5L13.5 17v4"/><path d="M19 3l-5.5 7v1"/><path d="M8 21h8"/>'),
  balance: P('<path d="M12 3v18"/><path d="M5 7h14"/><path d="M5 7l-3 6h6z"/><path d="M19 7l-3 6h6z"/><path d="M8 21h8"/>'),
  exit: P('<path d="M14 4h4a2 2 0 012 2v12a2 2 0 01-2 2h-4"/><path d="M10 8l-4 4 4 4"/><path d="M6 12h10"/>'),
  scorecard: P('<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h4"/>'),
  forecast: P('<path d="M3 16l5-5 3 3 4-6"/><path d="M15 8h4v4"/><path d="M15 19h6" stroke-dasharray="2 2.5"/><path d="M18 16v6" stroke-dasharray="2 2.5"/>'),
  // آیکون نوع نمودار
  chartBar: P('<path d="M5 20V11M12 20V4M19 20v-6"/>'),
  chartLine: P('<path d="M3 17l5-6 4 3 6-8"/>'),
  chartDonut: P('<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.2"/>'),
  chartFunnel: P('<path d="M4 5h16l-6 7v6l-4 2v-8z"/>'),
  chartScatter: P('<circle cx="7" cy="16" r="1.6"/><circle cx="12" cy="9" r="1.6"/><circle cx="17" cy="13" r="1.6"/><circle cx="9" cy="6" r="1.6"/>'),
  chartRadar: P('<path d="M12 3l8 6-3 9H7l-3-9z"/><path d="M12 8l3.5 2.6-1.3 4h-4.4l-1.3-4z"/>'),
  chartHeatmap: P('<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'),
  chartTable: P('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M9 9v11"/>'),
  chartGauge: P('<path d="M4 17a8 8 0 1116 0"/><path d="M12 17l4-4"/>'),
  chartHistogram: P('<path d="M4 20V14M9 20V8M14 20v-9M19 20v-4"/>'),
};

const CHART_ICON = {
  bar: 'chartBar', hbar: 'chartBar', stacked: 'chartBar', grouped: 'chartBar',
  line: 'chartLine', area: 'chartLine', donut: 'chartDonut', funnel: 'chartFunnel',
  scatter: 'chartScatter', radar: 'chartRadar', heatmap: 'chartHeatmap',
  table: 'chartTable', gauge: 'chartGauge', histogram: 'chartHistogram',
  diffbar: 'chartBar',
};

export function icon(name) {
  return icons[name] || icons.info;
}

export function chartIcon(type) {
  return icon(CHART_ICON[type] || 'chartBar');
}
