// صفحه فهرست سؤالات تحلیلی

import { fa, group } from '../format.js';
import { chartIcon, icon } from '../icons.js';

const LEVEL_INDEX = { descriptive: '۱', diagnostic: '۲', predictive: '۳' };

function questionCard(question, onOpen) {
  const card = document.createElement('button');
  card.className = 'qcard';
  card.type = 'button';
  card.innerHTML = `
    <div class="qcard__top">
      <div class="qcard__icon">${icon(question.icon)}</div>
      <div style="min-width:0">
        <div class="qcard__title">${fa(question.title)}</div>
        <div class="qcard__metric">${question.metric}</div>
      </div>
    </div>
    <div class="qcard__q">${fa(question.question)}</div>
    <div class="qcard__foot">
      <div class="qcard__charts" title="${fa(question.charts.join('، '))}">
        ${question.charts.slice(0, 3).map((c) => chartIcon(c)).join('')}
      </div>
      <span class="qcard__go">مشاهده تحلیل ${icon('arrowLeft')}</span>
    </div>`;
  card.addEventListener('click', () => onOpen(question.id));
  return card;
}

export function renderCatalog(root, catalog, { onOpen }) {
  const view = document.createElement('div');
  view.className = 'view';

  const summary = catalog.summary;
  view.innerHTML = `
    <div class="page-head">
      <h1 class="page-head__title">سؤالات تحلیلی</h1>
      <p class="page-head__lead">
        ${fa(
          `${catalog.questions.length} تحلیل در سه سطح، بر پایه ${
            summary ? group(summary.rows) : ''
          } رکورد درخواست جذب${summary ? ` طی ${group(summary.months)} ماه` : ''}. یک سؤال را انتخاب کنید تا خروجی کامل آن را ببینید.`
        )}
      </p>
    </div>
    <div class="search">
      ${icon('search')}
      <input type="search" id="qsearch" placeholder="جست‌وجو در سؤالات، متریک‌ها و برچسب‌ها…" aria-label="جست‌وجو در سؤالات" />
    </div>
    <div id="levels"></div>
    <div id="noResults"></div>`;

  root.textContent = '';
  root.appendChild(view);

  const levelsBox = view.querySelector('#levels');
  const noResults = view.querySelector('#noResults');
  const searchInput = view.querySelector('#qsearch');

  function paint(term = '') {
    const needle = term.trim().toLowerCase();
    levelsBox.textContent = '';
    noResults.textContent = '';
    let shown = 0;

    catalog.levels.forEach((level) => {
      const items = catalog.questions.filter((q) => {
        if (q.level !== level.key) return false;
        if (!needle) return true;
        const haystack = [q.title, q.question, q.metric, q.method, q.source, ...(q.tags || [])]
          .join(' ')
          .toLowerCase();
        return haystack.includes(needle);
      });
      if (!items.length) return;
      shown += items.length;

      const section = document.createElement('section');
      section.className = 'level';
      section.innerHTML = `
        <div class="level__head">
          <div class="level__badge">${LEVEL_INDEX[level.key] || ''}</div>
          <h2 class="level__title">${fa(level.label)}</h2>
          <span class="level__q">${fa(level.question)}</span>
          <div class="level__desc">${fa(level.description)}</div>
        </div>`;

      const grid = document.createElement('div');
      grid.className = 'qgrid';
      items.forEach((q) => grid.appendChild(questionCard(q, onOpen)));
      section.appendChild(grid);
      levelsBox.appendChild(section);
    });

    if (!shown) {
      noResults.innerHTML = `
        <div class="state">
          <div class="state__icon">${icon('search')}</div>
          <div class="state__title">سؤالی پیدا نشد</div>
          <div class="state__text">${fa(`هیچ سؤالی با «${term}» مطابقت نداشت. عبارت دیگری را امتحان کنید.`)}</div>
        </div>`;
    }
  }

  let timer = null;
  searchInput.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => paint(searchInput.value), 130);
  });

  paint();
}
