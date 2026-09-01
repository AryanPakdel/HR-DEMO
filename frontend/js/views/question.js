// صفحه سؤال: رندر عمومی پاسخ بک‌اند + فرم تعاملی مدل پیش‌بینی

import { fetchQuestion, predictTimeToFill, state } from '../api.js';
import { renderChart } from '../charts/index.js';
import { dataTable, insightList, kpiRow, skeleton, stateBlock, weightsPanel } from '../components.js';
import { days, fa, formatValue, group } from '../format.js';
import { icon } from '../icons.js';

const LEVEL_LABEL = {
  descriptive: 'تحلیل توصیفی',
  diagnostic: 'تحلیل تشخیصی',
  predictive: 'تحلیل پیش‌بینی',
};

export function renderQuestion(root, qid, { onBack, onOpen, catalog }) {
  const meta = catalog?.questions.find((q) => q.id === qid);
  const order = catalog?.order || [];
  const position = order.indexOf(qid);
  const prevId = position > 0 ? order[position - 1] : null;
  const nextId = position >= 0 && position < order.length - 1 ? order[position + 1] : null;

  const view = document.createElement('div');
  view.className = 'view';
  view.innerHTML = `
    <div class="qhead">
      <div class="crumbs">
        <button type="button" id="crumbHome">${fa('فهرست سؤالات')}</button>
        ${icon('chevron')}
        <span>${fa(meta ? LEVEL_LABEL[meta.level] : '')}</span>
      </div>
      <h1 class="qhead__title">${fa(meta?.title || '')}</h1>
      <p class="qhead__q">${fa(meta?.question || '')}</p>
      <div class="qhead__tags">
        <span class="chip chip--accent">${meta?.metric || ''}</span>
        ${(meta?.tags || []).map((t) => `<span class="chip">${fa(t)}</span>`).join('')}
      </div>
      <div class="method" id="method">
        <button class="method__toggle" type="button">
          ${icon('info')}<span>روش محاسبه و منبع تحلیل</span>
          <span style="flex:1"></span>${icon('chevron')}
        </button>
        <div class="method__body">
          <div class="method__row"><b>روش:</b><span>${fa(meta?.method || '')}</span></div>
          <div class="method__row"><b>منبع:</b><span>${fa(meta?.source || '')}</span></div>
          ${meta?.footnote ? `<div class="method__row"><b>توجه:</b><span>${fa(meta.footnote)}</span></div>` : ''}
        </div>
      </div>
    </div>
    <div id="toolbar"></div>
    <div id="content"></div>
    <div class="qnav" id="qnav"></div>`;

  root.textContent = '';
  root.appendChild(view);
  window.scrollTo({ top: 0, behavior: 'auto' });

  view.querySelector('#crumbHome').addEventListener('click', onBack);
  const methodBox = view.querySelector('#method');
  methodBox.querySelector('.method__toggle').addEventListener('click', () => {
    methodBox.classList.toggle('is-open');
  });

  const toolbarBox = view.querySelector('#toolbar');
  const contentBox = view.querySelector('#content');
  const navBox = view.querySelector('#qnav');

  // ناوبری سؤال قبلی و بعدی
  const navButton = (id, direction) => {
    const target = catalog.questions.find((q) => q.id === id);
    if (!target) return null;
    const btn = document.createElement('button');
    btn.className = `qnav__btn${direction === 'next' ? ' qnav__btn--next' : ''}`;
    btn.type = 'button';
    btn.innerHTML = `
      ${icon(direction === 'next' ? 'arrowLeft' : 'arrowRight')}
      <div>
        <div class="qnav__dir">${direction === 'next' ? 'سؤال بعدی' : 'سؤال قبلی'}</div>
        <div class="qnav__name">${fa(target.title)}</div>
      </div>`;
    btn.addEventListener('click', () => onOpen(id));
    return btn;
  };
  const prevBtn = prevId ? navButton(prevId, 'prev') : null;
  const nextBtn = nextId ? navButton(nextId, 'next') : null;
  if (prevBtn) navBox.appendChild(prevBtn);
  if (nextBtn) navBox.appendChild(nextBtn);

  // پارامترهای فعال صفحه (فیلترها، تب‌ها، وزن‌ها، ورودی مدل)
  const params = {};
  let toolbarBuilt = false;
  let charts = [];

  function clearCharts() {
    charts.forEach((c) => c.__cleanup?.());
    charts = [];
  }

  async function load({ keepToolbar = true } = {}) {
    clearCharts();
    contentBox.textContent = '';
    contentBox.appendChild(skeleton());

    try {
      const data = await fetchQuestion(qid, params);
      if (!keepToolbar || !toolbarBuilt) buildToolbar(data);
      paint(data);
    } catch (err) {
      contentBox.textContent = '';
      contentBox.appendChild(
        stateBlock({
          kind: 'error',
          title: err.message || 'محاسبه این تحلیل ممکن نشد',
          text: err.detail || (err.status === 401 ? 'برای ادامه، فایل داده را دوباره بارگذاری کنید.' : ''),
          action:
            err.status === 401
              ? { label: 'بازگشت به صفحه بارگذاری', onClick: () => (window.location.hash = '#/') }
              : { label: 'تلاش دوباره', onClick: () => load() },
        })
      );
    }
  }

  function buildToolbar(data) {
    toolbarBox.textContent = '';
    if (!data.filters.length && !data.tabs.length) return;

    const bar = document.createElement('div');
    bar.className = 'toolbar';

    data.tabs.forEach((tab) => {
      const field = document.createElement('div');
      field.className = 'field';
      field.innerHTML = `<label>${fa(tab.label)}</label>`;
      const seg = document.createElement('div');
      seg.className = 'segmented';
      const current = params[tab.key] || tab.options[0].value;
      params[tab.key] = current;

      tab.options.forEach((option) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = fa(option.label);
        btn.className = option.value === current ? 'is-active' : '';
        btn.addEventListener('click', () => {
          if (params[tab.key] === option.value) return;
          params[tab.key] = option.value;
          seg.querySelectorAll('button').forEach((b) => b.classList.remove('is-active'));
          btn.classList.add('is-active');
          load();
        });
        seg.appendChild(btn);
      });
      field.appendChild(seg);
      bar.appendChild(field);
    });

    data.filters.forEach((filter) => {
      const field = document.createElement('div');
      field.className = 'field';
      field.innerHTML = `<label for="f_${filter.key}">${fa(filter.label)}</label>`;
      const select = document.createElement('select');
      select.id = `f_${filter.key}`;

      const all = document.createElement('option');
      all.value = '__all__';
      all.textContent = fa(filter.allLabel || 'همه');
      select.appendChild(all);

      filter.options.forEach((option) => {
        const node = document.createElement('option');
        node.value = option.value;
        node.textContent = fa(option.label);
        select.appendChild(node);
      });
      select.value = params[filter.key] || '__all__';

      select.addEventListener('change', () => {
        if (select.value === '__all__') delete params[filter.key];
        else params[filter.key] = select.value;
        load();
      });
      field.appendChild(select);
      bar.appendChild(field);
    });

    const spacer = document.createElement('div');
    spacer.className = 'toolbar__spacer';
    bar.appendChild(spacer);

    const reset = document.createElement('button');
    reset.className = 'btn btn--ghost toolbar__reset';
    reset.type = 'button';
    reset.innerHTML = `${icon('reset')}بازنشانی فیلترها`;
    reset.addEventListener('click', () => {
      data.filters.forEach((f) => delete params[f.key]);
      bar.querySelectorAll('select').forEach((s) => {
        s.value = '__all__';
      });
      load();
    });
    bar.appendChild(reset);

    toolbarBox.appendChild(bar);
    toolbarBuilt = true;
  }

  function paint(data) {
    contentBox.textContent = '';
    let kpiBox = null;
    let insightBox = null;

    /**
     * کارت‌ها و بندهای تحلیلی که بک‌اند آنها را live علامت زده، مستقیماً از خروجی مدل
     * می‌آیند. با هر پیش‌بینی تازه فقط همین‌ها جایگزین می‌شوند تا عدد بالای صفحه و
     * عدد کارت‌ها هیچ‌وقت با هم اختلاف نداشته باشند.
     */
    const applyLive = (result) => {
      if (result.kpis?.length) {
        let next = 0;
        data.kpis = data.kpis.map((k) => (k.live ? result.kpis[next++] || k : k));
      }
      if (result.insight) {
        data.insights = data.insights.map((i) => (i.live ? result.insight : i));
      }
      if (kpiBox) {
        const fresh = kpiRow(data.kpis);
        kpiBox.replaceWith(fresh);
        kpiBox = fresh;
      }
      if (insightBox) {
        const fresh = insightList(data.insights);
        insightBox.replaceWith(fresh);
        insightBox = fresh;
      }
    };

    if (data.prediction && data.form) {
      contentBox.appendChild(predictPanel(data, params, load, applyLive));
      contentBox.appendChild(modelCard(data.model));
    }

    if (data.weights) {
      contentBox.appendChild(
        weightsPanel(data.weights, (payload) => {
          Object.assign(params, payload);
          load();
        })
      );
    }

    if (data.kpis.length) {
      kpiBox = kpiRow(data.kpis);
      contentBox.appendChild(kpiBox);
    }
    if (data.insights.length) {
      insightBox = insightList(data.insights);
      contentBox.appendChild(insightBox);
    }

    if (data.charts.length) {
      const grid = document.createElement('div');
      // دو نمودار کوچک کنار هم قرار می‌گیرند مگر آنکه نمودار عریض باشد
      const wide = data.charts.some((c) => ['line', 'area', 'heatmap', 'funnel'].includes(c.type));
      grid.className = `charts${!wide && data.charts.length > 1 ? ' charts--pair' : ''}`;
      data.charts.forEach((spec) => {
        const card = renderChart(spec);
        charts.push(card);
        grid.appendChild(card);
      });
      contentBox.appendChild(grid);
    }

    data.tables.forEach((spec) => contentBox.appendChild(dataTable(spec)));

    const note = data.footnote || data.meta?.footnote;
    if (note) {
      const foot = document.createElement('div');
      foot.className = 'tablecard__foot';
      foot.style.padding = '0 4px';
      foot.textContent = fa(note);
      contentBox.appendChild(foot);
    }

    if (!data.kpis.length && !data.charts.length && !data.tables.length) {
      contentBox.appendChild(
        stateBlock({
          title: 'نتیجه‌ای برای نمایش نیست',
          text: 'با فیلترهای انتخاب‌شده داده کافی وجود ندارد. فیلترها را بازنشانی کنید.',
        })
      );
    }
  }

  load({ keepToolbar: false });
  return () => clearCharts();
}

/* ─────────── پنل تعاملی مدل پیش‌بینی ─────────── */
function predictPanel(data, params, reload, onResult) {
  const wrap = document.createElement('div');
  wrap.className = 'predict';

  const { options, defaults, labels } = data.form;
  const form = document.createElement('div');
  form.className = 'predict__form';
  form.innerHTML = `
    <div class="predict__title">مشخصات پست تازه‌باز</div>
    <div class="predict__desc">
      ویژگی‌های یک پست را وارد کنید تا مدل زمان پر شدن آن را برآورد کند. همه این ویژگی‌ها
      پیش از شروع فرآیند جذب معلوم‌اند.
    </div>`;

  const grid = document.createElement('div');
  grid.className = 'predict__grid';
  const controls = {};

  const selectField = (key, values) => {
    const field = document.createElement('div');
    field.className = 'pfield';
    field.innerHTML = `<label for="p_${key}">${fa(labels[key] || key)}</label>`;
    const select = document.createElement('select');
    select.id = `p_${key}`;
    values.forEach((value) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = fa(value);
      select.appendChild(option);
    });
    select.value = params[key] || defaults[key];
    field.appendChild(select);
    grid.appendChild(field);
    controls[key] = select;
  };

  ['department', 'job_level', 'channel', 'recruiter', 'month'].forEach((key) => {
    if (options[key]?.length) selectField(key, options[key]);
  });

  const numField = document.createElement('div');
  numField.className = 'pfield';
  numField.innerHTML = `<label for="p_concurrent">${fa(labels.concurrent_openings)}</label>`;
  const numInput = document.createElement('input');
  numInput.type = 'number';
  numInput.id = 'p_concurrent';
  numInput.min = '1';
  numInput.max = '60';
  numInput.value = String(params.concurrent_openings || defaults.concurrent_openings);
  numField.appendChild(numInput);
  grid.appendChild(numField);
  controls.concurrent_openings = numInput;

  form.appendChild(grid);

  const out = document.createElement('div');
  out.className = `predict__out tone-${data.prediction.tone}`;

  function paintResult(result) {
    out.className = `predict__out tone-${result.tone}`;
    const toneChip =
      result.tone === 'bad' ? 'chip--bad' : result.tone === 'warn' ? 'chip--warn' : 'chip--good';
    out.innerHTML = `
      <div class="predict__label">زمان پیش‌بینی‌شده تا پر شدن پست</div>
      <div class="predict__value num">${group(result.days, 1)}<small>روز</small></div>
      <div class="predict__range">
        بازه اطمینان ۸۰٪: <b class="num">${group(result.lower, 1)}</b> تا
        <b class="num">${group(result.upper, 1)}</b> روز
      </div>
      <div class="predict__verdict">
        <span class="chip ${toneChip}">${fa(result.verdict)}</span>
        <span class="chip">${fa(
          `${result.vs_average >= 0 ? 'بالاتر' : 'پایین‌تر'} از میانگین: ${formatValue(
            Math.abs(result.vs_average),
            'days'
          )}`
        )}</span>
      </div>
      <div class="predict__bar">${rangeBar(result)}</div>`;
  }

  paintResult(data.prediction);

  let busy = false;
  async function submit() {
    if (busy) return;
    busy = true;
    const payload = {};
    Object.entries(controls).forEach(([key, node]) => {
      payload[key] = node.value;
      params[key] = node.value;
    });
    out.style.opacity = '0.5';
    try {
      const result = await predictTimeToFill(payload);
      paintResult(result);
      onResult?.(result);
    } catch (_) {
      // در صورت خطا، مسیر عمومی صفحه نتیجه را دوباره می‌گیرد
      reload();
    } finally {
      out.style.opacity = '1';
      busy = false;
    }
  }

  Object.values(controls).forEach((node) => {
    node.addEventListener('change', submit);
  });

  wrap.appendChild(form);
  wrap.appendChild(out);
  return wrap;
}

/** نوار نمایش بازه اطمینان نسبت به میانگین و آستانه سازمان */
function rangeBar(result) {
  const max = Math.max(result.upper, result.threshold) * 1.12;
  const pos = (v) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`;
  const color =
    result.tone === 'bad' ? 'var(--bad)' : result.tone === 'warn' ? 'var(--warn)' : 'var(--good)';
  const left = pos(result.lower);
  const width = `${Math.max(2, ((result.upper - result.lower) / max) * 100)}%`;

  return `
    <div style="position:relative;height:34px">
      <div style="position:absolute;inset-inline-end:0;top:12px;width:100%;height:6px;border-radius:99px;background:var(--surface-2)"></div>
      <div style="position:absolute;inset-inline-end:${left};top:12px;width:${width};height:6px;border-radius:99px;background:${color};opacity:.35"></div>
      <div style="position:absolute;inset-inline-end:${pos(result.days)};top:7px;width:3px;height:16px;border-radius:2px;background:${color};transform:translateX(50%)"></div>
      <div style="position:absolute;inset-inline-end:${pos(
        result.threshold
      )};top:5px;width:2px;height:20px;background:var(--warn);opacity:.7;transform:translateX(50%)"></div>
      <div style="position:absolute;inset-inline-end:${pos(
        result.threshold
      )};top:24px;font-size:10px;color:var(--warn);transform:translateX(50%);white-space:nowrap">آستانه ${fa(
    group(result.threshold, 0)
  )}</div>
    </div>`;
}

function modelCard(model) {
  const card = document.createElement('div');
  card.className = 'modelcard';
  const m = model.metrics;
  card.innerHTML = `
    <div class="modelcard__head">
      <div class="modelcard__icon">${icon('forecast')}</div>
      <div>
        <div class="chart__title">کارت مدل</div>
        <div class="chart__subtitle">${fa(`${model.algorithm} · ${model.split} · ${model.quantile}`)}</div>
      </div>
    </div>
    <div class="modelcard__grid">
      <div class="modelcard__cell"><b class="num">${group(m.r2, 3)}</b><span>ضریب تعیین (R²)</span></div>
      <div class="modelcard__cell"><b class="num">${group(m.mae, 2)}</b><span>خطای مطلق میانگین (روز)</span></div>
      <div class="modelcard__cell"><b class="num">${group(m.rmse, 2)}</b><span>ریشه میانگین مربعات خطا</span></div>
      <div class="modelcard__cell"><b class="num">${group(m.train_size)}</b><span>نمونه آموزش</span></div>
      <div class="modelcard__cell"><b class="num">${group(m.test_size)}</b><span>نمونه آزمون</span></div>
      <div class="modelcard__cell"><b class="num">${group(m.coverage * 100, 1)}٪</b><span>پوشش واقعی بازه اطمینان</span></div>
    </div>`;
  return card;
}
