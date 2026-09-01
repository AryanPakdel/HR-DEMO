// صفحه بارگذاری فایل اکسل

import { ApiError, loadSample, setSession, uploadFile } from '../api.js';
import { fa, group } from '../format.js';
import { icon } from '../icons.js';

const SAMPLE_COLUMNS = [
  'department', 'job_level', 'channel', 'recruiter', 'month', 'time_to_fill',
  'hr_processing_days', 'applicants', 'screened', 'interviewed', 'offered',
  'accepted', 'total_cost', 'hired', 'first_year_turnover', 'performance_score_6m',
];

export function renderUpload(root, { onReady }) {
  const view = document.createElement('div');
  view.className = 'view upload';
  view.innerHTML = `
    <div class="upload__eyebrow">تحلیل توصیفی، تشخیصی و پیش‌بینی</div>
    <h1 class="upload__title">داشبورد تحلیل <span>جذب و استخدام</span></h1>
    <p class="upload__lead">
      فایل اکسل داده جذب و استخدام را بارگذاری کنید تا ۱۴ تحلیل در سه سطح، به‌صورت
      نمودار، جدول و تحلیل متنی در اختیار شما قرار گیرد.
    </p>

    <label class="dropzone" id="dropzone">
      <div class="dropzone__icon">${icon('upload')}</div>
      <div class="dropzone__title">فایل اکسل را اینجا رها کنید</div>
      <div class="dropzone__hint">یا برای انتخاب از رایانه کلیک کنید — فرمت xlsx</div>
      <input type="file" accept=".xlsx,.xlsm" id="fileInput" />
    </label>

    <div class="upload__divider">یا</div>

    <div class="upload__actions">
      <button class="btn" id="sampleBtn" type="button">${icon('file')}بارگذاری داده نمونه</button>
    </div>

    <div id="uploadState"></div>

    <div class="schema">
      <div class="schema__title">${icon('info')} ساختار مورد انتظار فایل</div>
      <div class="schema__text">
        فایل باید یک شیت با ۳۷ ستون داشته باشد و هر ردیف نماینده یک درخواست جذب باشد.
        ستون‌های کلیدی مورد نیاز عبارت‌اند از:
      </div>
      <div class="schema__cols">
        ${SAMPLE_COLUMNS.map((c) => `<span class="schema__col">${c}</span>`).join('')}
        <span class="schema__col">…</span>
      </div>
    </div>`;

  root.textContent = '';
  root.appendChild(view);

  const dropzone = view.querySelector('#dropzone');
  const fileInput = view.querySelector('#fileInput');
  const sampleBtn = view.querySelector('#sampleBtn');
  const stateBox = view.querySelector('#uploadState');
  let busy = false;

  function setBusy(on, label) {
    busy = on;
    sampleBtn.disabled = on;
    dropzone.style.pointerEvents = on ? 'none' : '';
    if (on) {
      stateBox.innerHTML = `
        <div class="state">
          <div style="display:flex;align-items:center;gap:10px;justify-content:center;color:var(--accent)">
            <span class="spinner"></span><span>${fa(label)}</span>
          </div>
        </div>`;
    }
  }

  function showError(err) {
    const missing = err instanceof ApiError ? err.missing : [];
    stateBox.innerHTML = `
      <div class="state state--error">
        <div class="state__icon">${icon('alert')}</div>
        <div class="state__title">${fa(err.message || 'بارگذاری ناموفق بود')}</div>
        ${err.detail ? `<div class="state__text">${fa(err.detail)}</div>` : ''}
        ${
          missing.length
            ? `<div class="state__text">ستون‌های زیر در فایل یافت نشدند:</div>
               <div class="state__cols">${missing
                 .slice(0, 24)
                 .map((m) => `<span class="schema__col">${m.key || m}</span>`)
                 .join('')}${
                missing.length > 24 ? `<span class="schema__col">و ${missing.length - 24} ستون دیگر</span>` : ''
              }</div>`
            : ''
        }
      </div>`;
  }

  function showSuccess(payload) {
    const s = payload.summary;
    stateBox.innerHTML = `
      <div class="card summary" style="padding:24px;text-align:right;margin-top:24px">
        <div class="summary__head">
          <div class="summary__check">${icon('check')}</div>
          <div>
            <div style="font-weight:700;font-size:16px">فایل با موفقیت خوانده شد</div>
            <div style="font-size:13px;color:var(--text-muted)">${fa(s.period_label)}</div>
          </div>
        </div>
        <div class="summary__grid">
          <div class="summary__cell"><b class="num">${group(s.rows)}</b><span>رکورد درخواست جذب</span></div>
          <div class="summary__cell"><b class="num">${group(s.hires)}</b><span>استخدام نهایی</span></div>
          <div class="summary__cell"><b class="num">${group(s.months)}</b><span>ماه پوشش زمانی</span></div>
          <div class="summary__cell"><b class="num">${group(s.departments)}</b><span>واحد سازمانی</span></div>
          <div class="summary__cell"><b class="num">${group(s.channels)}</b><span>کانال جذب</span></div>
          <div class="summary__cell"><b class="num">${group(s.recruiters)}</b><span>کارشناس جذب</span></div>
        </div>
      </div>`;
    setTimeout(() => onReady(payload), 620);
  }

  async function handle(promise, label) {
    if (busy) return;
    setBusy(true, label);
    try {
      const payload = await promise;
      setSession(payload);
      showSuccess(payload);
    } catch (err) {
      showError(err);
    } finally {
      busy = false;
      sampleBtn.disabled = false;
      dropzone.style.pointerEvents = '';
    }
  }

  fileInput.addEventListener('change', () => {
    const file = fileInput.files?.[0];
    // مقدار input خالی می‌شود تا انتخاب دوباره همان فایل هم رویداد change را بفرستد
    fileInput.value = '';
    if (file) handle(uploadFile(file), 'در حال خواندن و اعتبارسنجی فایل…');
  });

  ['dragenter', 'dragover'].forEach((type) =>
    dropzone.addEventListener(type, (e) => {
      e.preventDefault();
      dropzone.classList.add('is-over');
    })
  );
  ['dragleave', 'drop'].forEach((type) =>
    dropzone.addEventListener(type, (e) => {
      e.preventDefault();
      dropzone.classList.remove('is-over');
    })
  );
  dropzone.addEventListener('drop', (e) => {
    const file = e.dataTransfer?.files?.[0];
    if (file) handle(uploadFile(file), 'در حال خواندن و اعتبارسنجی فایل…');
  });

  sampleBtn.addEventListener('click', () => handle(loadSample(), 'در حال بارگذاری داده نمونه…'));
}
