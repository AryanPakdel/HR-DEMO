// لایه ارتباط با بک‌اند و نگهداری شناسه نشست

const SESSION_KEY = 'hr_analytics_session';

export const state = {
  sessionId: sessionStorage.getItem(SESSION_KEY) || '',
  summary: null,
  catalog: null,
};

export function setSession(payload) {
  state.sessionId = payload.session_id;
  state.summary = payload.summary;
  try {
    sessionStorage.setItem(SESSION_KEY, payload.session_id);
    sessionStorage.setItem(`${SESSION_KEY}_summary`, JSON.stringify(payload.summary));
  } catch (_) {
    // حالت مرورگر خصوصی؛ نشست فقط در حافظه می‌ماند
  }
}

export function restoreSummary() {
  if (state.summary) return state.summary;
  try {
    const raw = sessionStorage.getItem(`${SESSION_KEY}_summary`);
    if (raw) state.summary = JSON.parse(raw);
  } catch (_) {
    state.summary = null;
  }
  return state.summary;
}

export function clearSession() {
  state.sessionId = '';
  state.summary = null;
  state.catalog = null;
  try {
    sessionStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem(`${SESSION_KEY}_summary`);
  } catch (_) {
    /* بی‌اهمیت */
  }
}

/** خطای قابل نمایش به کاربر با جزئیات ساختاری از بک‌اند */
export class ApiError extends Error {
  constructor(message, { status = 0, missing = [], detail = '' } = {}) {
    super(message);
    this.status = status;
    this.missing = missing;
    this.detail = detail;
  }
}

async function parse(response) {
  let body = null;
  try {
    body = await response.json();
  } catch (_) {
    body = null;
  }
  if (response.ok) return body;

  const message =
    (body && (body.message || (typeof body.detail === 'string' ? body.detail : null))) ||
    'درخواست با خطا مواجه شد.';
  throw new ApiError(message, {
    status: response.status,
    missing: (body && body.missing) || [],
    detail: (body && body.detail) || '',
  });
}

export async function uploadFile(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch('/api/upload', { method: 'POST', body: form });
  return parse(res);
}

export async function loadSample() {
  const res = await fetch('/api/sample', { method: 'POST' });
  return parse(res);
}

export async function fetchCatalog() {
  const res = await fetch(`/api/questions?session_id=${encodeURIComponent(state.sessionId)}`);
  const data = await parse(res);
  state.catalog = data;
  return data;
}

export async function fetchQuestion(qid, params = {}) {
  const search = new URLSearchParams({ session_id: state.sessionId });
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value);
  });
  const res = await fetch(`/api/questions/${encodeURIComponent(qid)}?${search}`);
  return parse(res);
}

export async function predictTimeToFill(payload) {
  const res = await fetch('/api/predict/time-to-fill', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, session_id: state.sessionId }),
  });
  return parse(res);
}
