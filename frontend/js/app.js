// بوت‌استرپ اپلیکیشن و مسیریابی مبتنی بر hash

import { clearSession, fetchCatalog, restoreSummary, state } from './api.js';
import { setCurrency, fa, group } from './format.js';
import { icon } from './icons.js';
import { renderCatalog } from './views/catalog.js';
import { renderQuestion } from './views/question.js';
import { renderUpload } from './views/upload.js';

const THEME_KEY = 'hr_analytics_theme';

function initTheme() {
  let saved = null;
  try {
    saved = localStorage.getItem(THEME_KEY);
  } catch (_) {
    saved = null;
  }
  const theme = saved || 'dark';
  document.documentElement.setAttribute('data-theme', theme);
  return theme;
}

function toggleTheme(button) {
  const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch (_) {
    /* حالت مرورگر خصوصی */
  }
  paintThemeButton(button, next);
}

function paintThemeButton(button, theme) {
  button.innerHTML = icon(theme === 'dark' ? 'sun' : 'moon');
  const label = theme === 'dark' ? 'تغییر به حالت روشن' : 'تغییر به حالت تیره';
  button.title = label;
  button.setAttribute('aria-label', label);
}

function buildShell() {
  const app = document.createElement('div');
  app.className = 'app';
  app.innerHTML = `
    <header class="header">
      <div class="brand" id="brand" role="button" tabindex="0">
        <div class="brand__mark">${icon('logo')}</div>
        <div class="brand__text">
          <span class="brand__title">تحلیل جذب و استخدام</span>
          <span class="brand__sub">توصیفی · تشخیصی · پیش‌بینی</span>
        </div>
      </div>
      <div class="header__spacer"></div>
      <div class="header__meta" id="headerMeta" hidden></div>
      <button class="icon-btn" id="themeBtn" type="button"></button>
      <button class="icon-btn" id="resetBtn" type="button" title="بارگذاری فایل جدید" aria-label="بارگذاری فایل جدید" hidden>
        ${icon('refresh')}
      </button>
    </header>
    <main class="main" id="main"></main>
    <footer class="footer">
      داشبورد تحلیل جذب و استخدام · ساخته‌شده بر پایه فایل نقشه تحلیل توصیفی، تشخیصی و پیش‌بینی
    </footer>`;
  document.body.appendChild(app);
  return app;
}

const shell = buildShell();
const main = shell.querySelector('#main');
const headerMeta = shell.querySelector('#headerMeta');
const resetBtn = shell.querySelector('#resetBtn');
const themeBtn = shell.querySelector('#themeBtn');

paintThemeButton(themeBtn, initTheme());
themeBtn.addEventListener('click', () => toggleTheme(themeBtn));

shell.querySelector('#brand').addEventListener('click', () => {
  window.location.hash = state.sessionId ? '#/questions' : '#/';
});

resetBtn.addEventListener('click', () => {
  clearSession();
  window.location.hash = '#/';
  navigate();
});

function paintHeaderMeta() {
  const summary = state.summary || restoreSummary();
  if (!summary || !state.sessionId) {
    headerMeta.hidden = true;
    resetBtn.hidden = true;
    return;
  }
  headerMeta.hidden = false;
  resetBtn.hidden = false;
  headerMeta.innerHTML = `${icon('file')}<span><b class="num">${group(summary.rows)}</b> رکورد · <b class="num">${group(
    summary.months
  )}</b> ماه</span>`;
  headerMeta.querySelector('svg').style.width = '14px';
  headerMeta.querySelector('svg').style.height = '14px';
}

let cleanup = null;

async function ensureCatalog() {
  if (state.catalog) return state.catalog;
  const catalog = await fetchCatalog();
  setCurrency(catalog.currency);
  if (catalog.summary) state.summary = catalog.summary;
  return catalog;
}

function showLoading() {
  main.innerHTML = `
    <div class="state">
      <div style="display:flex;align-items:center;gap:10px;justify-content:center;color:var(--accent)">
        <span class="spinner"></span><span>در حال بارگذاری…</span>
      </div>
    </div>`;
}

async function navigate() {
  if (cleanup) {
    cleanup();
    cleanup = null;
  }
  const hash = window.location.hash.replace(/^#/, '') || '/';
  const [, route, param] = hash.split('/');

  if (!state.sessionId) restoreSummary();

  // بدون نشست فعال، همه مسیرها به صفحه بارگذاری برمی‌گردند
  if (!state.sessionId && route !== '') {
    window.location.hash = '#/';
    return;
  }

  paintHeaderMeta();

  if (!route) {
    renderUpload(main, {
      onReady: () => {
        state.catalog = null;
        window.location.hash = '#/questions';
      },
    });
    paintHeaderMeta();
    return;
  }

  showLoading();
  let catalog;
  try {
    catalog = await ensureCatalog();
  } catch (err) {
    // نشست منقضی یا سرور در دسترس نیست
    clearSession();
    window.location.hash = '#/';
    navigate();
    return;
  }
  paintHeaderMeta();

  if (route === 'questions' && !param) {
    renderCatalog(main, catalog, {
      onOpen: (qid) => {
        window.location.hash = `#/questions/${qid}`;
      },
    });
    return;
  }

  if (route === 'questions' && param) {
    if (!catalog.questions.some((q) => q.id === param)) {
      window.location.hash = '#/questions';
      return;
    }
    cleanup = renderQuestion(main, param, {
      catalog,
      onBack: () => {
        window.location.hash = '#/questions';
      },
      onOpen: (qid) => {
        window.location.hash = `#/questions/${qid}`;
      },
    });
    return;
  }

  window.location.hash = state.sessionId ? '#/questions' : '#/';
}

window.addEventListener('hashchange', navigate);
navigate();
