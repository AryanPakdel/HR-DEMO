// اجزای رابط کاربری: KPI، تحلیل متنی، جدول، حالت‌ها و اسلایدر وزن‌دهی

import { fa, formatValue, splitUnit } from './format.js';
import { icon } from './icons.js';

const INSIGHT_ICON = { good: 'good', warn: 'alert', bad: 'alert', info: 'info' };

export function kpiRow(kpis) {
  const wrap = document.createElement('div');
  wrap.className = 'kpis';
  kpis.forEach((k) => {
    const { value, unit } = splitUnit(k.value, k.format);
    const card = document.createElement('div');
    card.className = `kpi${k.tone && k.tone !== 'neutral' ? ` kpi--${k.tone}` : ''}`;
    const isText = k.format === 'text' || typeof k.value === 'string';
    card.innerHTML = `
      <div class="kpi__label">${fa(k.label)}</div>
      <div class="kpi__value num${isText ? ' is-text' : ''}">${value}${
      unit ? `<span class="kpi__unit">${unit}</span>` : ''
    }</div>
      ${k.hint ? `<div class="kpi__hint">${fa(k.hint)}</div>` : ''}`;
    wrap.appendChild(card);
  });
  return wrap;
}

export function insightList(insights) {
  const wrap = document.createElement('div');
  wrap.className = 'insights';
  insights.forEach((item) => {
    const node = document.createElement('div');
    node.className = `insight insight--${item.tone || 'info'}`;
    node.innerHTML = `
      <span class="insight__icon">${icon(INSIGHT_ICON[item.tone] || 'info')}</span>
      <div>
        ${item.title ? `<div class="insight__title">${fa(item.title)}</div>` : ''}
        <div class="insight__text">${fa(item.text)}</div>
      </div>`;
    wrap.appendChild(node);
  });
  return wrap;
}

/** قالب‌بندی سلول؛ نوع dynamic از ستون format خود ردیف پیروی می‌کند */
function cellFormat(column, row) {
  return column.format === 'dynamic' ? row.format || 'number' : column.format;
}

export function dataTable(spec) {
  const card = document.createElement('div');
  card.className = 'tablecard';

  const head = document.createElement('div');
  head.className = 'tablecard__head';
  head.innerHTML = `
    <div>
      <div class="tablecard__title">${fa(spec.title)}</div>
      ${spec.subtitle ? `<div class="tablecard__subtitle">${fa(spec.subtitle)}</div>` : ''}
    </div>`;

  const exportBtn = document.createElement('button');
  exportBtn.className = 'icon-btn';
  exportBtn.type = 'button';
  exportBtn.title = 'دانلود جدول با فرمت CSV';
  exportBtn.setAttribute('aria-label', 'دانلود جدول');
  exportBtn.innerHTML = icon('download');
  exportBtn.addEventListener('click', () => downloadCsv(spec));
  head.appendChild(exportBtn);
  card.appendChild(head);

  const wrap = document.createElement('div');
  wrap.className = 'tablewrap';
  const table = document.createElement('table');
  table.className = 'data';

  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  spec.columns.forEach((column, ci) => {
    const th = document.createElement('th');
    th.innerHTML = `${fa(column.label)}<span class="sort"></span>`;
    th.addEventListener('click', () => sortBy(ci));
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  table.appendChild(tbody);
  wrap.appendChild(table);
  card.appendChild(wrap);

  if (spec.footnote) {
    const foot = document.createElement('div');
    foot.className = 'tablecard__foot';
    foot.textContent = fa(spec.footnote);
    card.appendChild(foot);
  }

  // بیشینه مقدار هر ستون میله‌ای، برای مقیاس میله درون‌سلولی
  const maxima = {};
  spec.columns.forEach((column) => {
    if (!column.bar) return;
    const values = spec.rows.map((r) => Math.abs(Number(r[column.key]))).filter(Number.isFinite);
    maxima[column.key] = values.length ? Math.max(...values) : 1;
  });

  let rows = spec.rows.slice();
  let sortIndex = -1;
  let ascending = false;

  function paint() {
    tbody.textContent = '';
    rows.forEach((row) => {
      const tr = document.createElement('tr');
      spec.columns.forEach((column) => {
        const td = document.createElement('td');
        const raw = row[column.key];
        const format = cellFormat(column, row);

        if (format === 'badge') {
          if (raw) {
            td.innerHTML = `<span class="badge badge--${row[column.toneKey] || 'neutral'}">${fa(raw)}</span>`;
          }
        } else if (column.bar && Number.isFinite(Number(raw))) {
          const ratio = Math.min(1, Math.abs(Number(raw)) / (maxima[column.key] || 1));
          td.className = 'is-num';
          td.innerHTML = `<span class="cellbar"><span class="cellbar__fill" style="width:${(
            ratio * 100
          ).toFixed(1)}%"></span><span class="cellbar__text">${formatValue(raw, format)}</span></span>`;
        } else {
          td.textContent = formatValue(raw, format);
          if (typeof raw === 'number') {
            td.className = 'is-num';
            // ستون‌های اختلافی: علامت با رنگ معنایی همراه می‌شود
            if (format.startsWith('delta') && raw !== 0) {
              td.classList.add(raw > 0 ? 'is-pos' : 'is-neg');
            }
          }
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    headRow.querySelectorAll('.sort').forEach((node, i) => {
      node.textContent = i === sortIndex ? (ascending ? '▲' : '▼') : '';
    });
  }

  function sortBy(index) {
    const key = spec.columns[index].key;
    ascending = sortIndex === index ? !ascending : false;
    sortIndex = index;
    rows.sort((a, b) => {
      const av = a[key];
      const bv = b[key];
      const an = Number(av);
      const bn = Number(bv);
      const numeric = Number.isFinite(an) && Number.isFinite(bn);
      const cmp = numeric ? an - bn : String(av ?? '').localeCompare(String(bv ?? ''), 'fa');
      return ascending ? cmp : -cmp;
    });
    paint();
  }

  paint();
  return card;
}

function downloadCsv(spec) {
  const escape = (value) => {
    const s = String(value ?? '');
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = spec.columns.map((c) => escape(c.label)).join(',');
  const body = spec.rows
    .map((row) => spec.columns.map((c) => escape(row[c.key])).join(','))
    .join('\n');
  // BOM تا اکسل فارسی را درست تشخیص دهد
  const blob = new Blob([`﻿${header}\n${body}`], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${spec.title.slice(0, 40) || 'table'}.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

export function weightsPanel(config, onChange) {
  const card = document.createElement('div');
  card.className = 'weights';
  card.innerHTML = `
    <div class="weights__head">
      <div>
        <div class="weights__title">${fa(config.title)}</div>
        <div class="weights__desc">${fa(config.description)}</div>
      </div>
    </div>`;

  const resetBtn = document.createElement('button');
  resetBtn.className = 'btn btn--ghost';
  resetBtn.type = 'button';
  resetBtn.innerHTML = `${icon('reset')}بازنشانی وزن‌ها`;
  card.querySelector('.weights__head').appendChild(resetBtn);

  const grid = document.createElement('div');
  grid.className = 'weights__grid';
  const inputs = [];

  config.items.forEach((item) => {
    const field = document.createElement('div');
    field.innerHTML = `
      <div class="weight__top">
        <div>
          <span class="weight__label">${fa(item.label)}</span>
          <div class="weight__dir">${item.higherIsBetter ? 'بیشتر بهتر است' : 'کمتر بهتر است'}</div>
        </div>
        <span class="weight__value num">${fa(item.value)}</span>
      </div>`;

    const range = document.createElement('input');
    range.type = 'range';
    range.min = '0';
    range.max = '50';
    range.step = '1';
    range.value = String(item.value);
    range.setAttribute('aria-label', item.label);
    const readout = field.querySelector('.weight__value');

    let timer = null;
    range.addEventListener('input', () => {
      readout.textContent = fa(range.value);
      // درخواست فقط پس از توقف حرکت اسلایدر ارسال می‌شود
      clearTimeout(timer);
      timer = setTimeout(emit, 260);
    });

    field.appendChild(range);
    grid.appendChild(field);
    inputs.push({ key: item.key, range, readout, default: item.default });
  });

  function emit() {
    const payload = {};
    inputs.forEach((i) => {
      payload[`w_${i.key}`] = i.range.value;
    });
    onChange(payload);
  }

  resetBtn.addEventListener('click', () => {
    inputs.forEach((i) => {
      i.range.value = String(i.default);
      i.readout.textContent = fa(i.default);
    });
    emit();
  });

  card.appendChild(grid);
  return card;
}

export function stateBlock({ kind = 'empty', title, text, columns = [], action }) {
  const wrap = document.createElement('div');
  wrap.className = `state${kind === 'error' ? ' state--error' : ''}`;
  wrap.innerHTML = `
    <div class="state__icon">${icon(kind === 'error' ? 'alert' : 'search')}</div>
    <div class="state__title">${fa(title)}</div>
    ${text ? `<div class="state__text">${fa(text)}</div>` : ''}
    ${
      columns.length
        ? `<div class="state__cols">${columns
            .map((c) => `<span class="schema__col">${c.key || c}</span>`)
            .join('')}</div>`
        : ''
    }`;
  if (action) {
    const btn = document.createElement('button');
    btn.className = 'btn btn--primary';
    btn.type = 'button';
    btn.textContent = action.label;
    btn.addEventListener('click', action.onClick);
    wrap.appendChild(btn);
  }
  return wrap;
}

export function skeleton() {
  const wrap = document.createElement('div');
  wrap.innerHTML = `
    <div class="skel-kpis">
      ${'<div class="skeleton skel-kpi"></div>'.repeat(4)}
    </div>
    <div class="skeleton skel-chart"></div>
    <div class="skeleton skel-chart" style="height:260px"></div>`;
  return wrap;
}
