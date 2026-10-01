const API = '/api/v1';
const $ = (id) => document.getElementById(id);

const EXAMPLES = {
  'Nested loops & ifs': `def helper(x):
    return x * 2 + 10


def process_data():
    data = [1, 2, 3, 4, 5]
    result = []
    for item in data:
        if item > 2:
            result.append(helper(item))
    return result
`,
  'Verbose grade function': `def grade(score):
    if score >= 90:
        result = "A"
    else:
        if score >= 80:
            result = "B"
        else:
            if score >= 70:
                result = "C"
            else:
                result = "F"
    return result


def report(scores):
    out = []
    for s in scores:
        out.append(grade(s))
    return out
`,
  'Classes & calls': `class Cart:
    def total(self, prices):
        t = 0
        for p in prices:
            t = t + p
        return t


def checkout(prices):
    cart = Cart()
    amount = cart.total(prices)
    if amount > 100:
        amount = amount - amount * 0.1
    return amount
`,
};

// ─── helpers ────────────────────────────────────────────────────────────────
const store = {
  get: (k) => { try { return localStorage.getItem(k) || ''; } catch (_) { return ''; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch (_) { /* storage unavailable */ } },
};
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function setStatus(text, kind = '') {
  $('status-text').textContent = text;
  $('status-dot').className = `dot ${kind}`;
}
function showError(msg) { const e = $('error'); e.textContent = msg; e.hidden = !msg; }
function setBusy(btn, busy) {
  $('analyze-btn').disabled = busy;
  $('refactor-btn').disabled = busy;
  btn.classList.toggle('busy', busy);
}
function headers() {
  const h = { 'Content-Type': 'application/json' };
  const key = store.get('accessKey');
  if (key) h['X-Access-Key'] = key;
  return h;
}
async function failure(res) {
  let detail = res.statusText;
  try {
    const body = await res.json();
    detail = body.detail || detail;
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join('; ');
  } catch (_) { /* non-JSON error body */ }
  if (res.status === 401) detail = 'Access key required — click 🔑 to set it.';
  return new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
}
async function post(path, body, asText = false) {
  const res = await fetch(API + path, { method: 'POST', headers: headers(), body: JSON.stringify(body) });
  if (!res.ok) throw await failure(res);
  return asText ? res.text() : res.json();
}

// ─── editor (CodeMirror when available, plain textarea otherwise) ───────────
const textarea = $('source-code');
const hasCM = typeof window.CodeMirror !== 'undefined';
const cm = hasCM
  ? window.CodeMirror.fromTextArea(textarea, {
    mode: 'python', lineNumbers: true, matchBrackets: true, autoCloseBrackets: true,
    indentUnit: 4, tabSize: 4, indentWithTabs: false, styleActiveLine: false,
    extraKeys: { Tab: (c) => c.replaceSelection('    ', 'end') },
  })
  : null;
const getCode = () => (cm ? cm.getValue() : textarea.value);
const setCode = (v) => { if (cm) cm.setValue(v); else textarea.value = v; };
if (cm) {
  cm.on('cursorActivity', () => {
    const { line, ch } = cm.getCursor();
    $('cursor-pos').textContent = `Ln ${line + 1}, Col ${ch + 1}`;
  });
}
Object.keys(EXAMPLES).forEach((name) => $('examples').add(new Option(name, name)));
$('examples').addEventListener('change', (e) => {
  if (!e.target.value) return;
  setCode(EXAMPLES[e.target.value]);
  e.target.value = '';
  $('target-function').innerHTML = '<option value="">Analyze to list functions</option>';
});
setCode(EXAMPLES['Nested loops & ifs']);

// ─── tabs ───────────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.tab-content').forEach((c) => c.classList.toggle('active', c.id === `tab-${name}`));
  if (name === 'graph') fitGraph();
  if (name === 'result') setTimeout(() => viewers.forEach((v) => v.refresh()), 0);
}
document.querySelectorAll('.tab').forEach((t) => t.addEventListener('click', () => switchTab(t.dataset.tab)));

// vis-network sizes itself while the iframe is hidden, so re-fit once the Graph tab is visible.
function fitGraph() {
  setTimeout(() => {
    try {
      const w = $('graph-frame').contentWindow;
      w.network.redraw();
      w.network.fit();
    } catch (_) { /* graph not loaded yet */ }
  }, 150);
}

// ─── header pills ───────────────────────────────────────────────────────────
async function loadHealth() {
  try {
    const h = await (await fetch(`${API}/health`)).json();
    $('pill-model').textContent = `model: ${h.model}`;
    const p = $('pill-sandbox');
    p.textContent = `sandbox: ${h.sandbox}`;
    p.classList.add(h.sandbox === 'docker' ? 'ok' : 'warn');
    p.title = h.sandbox === 'docker' ? 'Code runs in isolated Docker containers'
      : 'Docker unavailable — reduced isolation';
  } catch (_) {
    $('pill-sandbox').textContent = 'api: offline';
    $('pill-sandbox').classList.add('warn');
  }
}
$('key-btn').addEventListener('click', () => {
  const key = window.prompt('Access key for this deployment (leave empty to clear):', store.get('accessKey'));
  if (key !== null) { store.set('accessKey', key.trim()); setStatus(key.trim() ? 'Access key saved' : 'Access key cleared'); }
});

// ─── analyze ────────────────────────────────────────────────────────────────
async function analyze() {
  showError('');
  setBusy($('analyze-btn'), true);
  setStatus('Analyzing...', 'busy');
  try {
    const source_code = getCode();
    const data = await post('/analyze', { source_code });
    const select = $('target-function');
    const previous = select.value;
    select.innerHTML = '';
    data.functions.forEach((f) => select.add(new Option(f, f)));
    if (!data.functions.length) select.add(new Option('No functions found', ''));
    else if (data.functions.includes(previous)) select.value = previous;

    $('graph-frame').srcdoc = await post('/visualize', { source_code }, true);
    $('graph-frame').hidden = false;
    $('graph-legend').hidden = false;
    $('graph-empty').hidden = true;
    setStatus(`✅ Done — ${data.functions.length} function(s), ${data.graph_data.edges.length} call edge(s)`, 'ok');
  } catch (e) {
    showError(e.message);
    setStatus('Analysis failed', 'err');
  } finally {
    setBusy($('analyze-btn'), false);
  }
}

// ─── diff ───────────────────────────────────────────────────────────────────
// Line-level LCS diff: returns which original lines were removed / refactored lines added.
function diffLines(a, b) {
  const n = a.length, m = b.length;
  const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const removed = new Set(), added = new Set();
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) removed.add(i++);
    else added.add(j++);
  }
  while (i < n) removed.add(i++);
  while (j < m) added.add(j++);
  return { removed, added };
}
const viewers = [];
function renderCode(el, lines, marked, cls) {
  if (!hasCM) {
    el.innerHTML = `<pre class="fallback">${lines
      .map((l, i) => `<span class="${marked.has(i) && l.trim() ? 'line-' + cls : ''}">${esc(l) || ' '}</span>`)
      .join('')}</pre>`;
    return;
  }
  el.innerHTML = '';
  const v = window.CodeMirror(el, {
    value: lines.join('\n'), mode: 'python', lineNumbers: true, readOnly: true, viewportMargin: Infinity,
  });
  lines.forEach((l, i) => { if (marked.has(i) && l.trim()) v.addLineClass(i, 'background', `line-${cls}`); });
  viewers.push(v);
  setTimeout(() => v.refresh(), 0);
}
function renderResult(data) {
  const a = data.original_code.split('\n');
  const b = data.refactored_code.split('\n');
  const { removed, added } = diffLines(a, b);
  viewers.length = 0;
  renderCode($('original-code'), a, removed, 'removed');
  renderCode($('refactored-code'), b, added, 'added');
  $('graph-context').textContent = `Retrieved context → ${data.graph_context}`;
  const eq = $('equiv-badge');
  const verified = (data.equivalence || '').startsWith('Behavior verified');
  eq.hidden = !data.equivalence;
  eq.className = `badge ${verified ? 'good' : 'warn'}`;
  eq.textContent = `${verified ? '✓' : '⚠'} ${data.equivalence || ''}`;
  $('result-empty').hidden = true;
  $('result').hidden = false;
  viewers.forEach((v) => v.refresh());
  currentRefactored = data.refactored_code;
}
let currentRefactored = '';
$('copy-btn').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(currentRefactored); setStatus('Copied refactored code', 'ok'); }
  catch (_) { setStatus('Copy failed — select the code manually', 'err'); }
});
$('download-btn').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([currentRefactored], { type: 'text/x-python' }));
  const a = Object.assign(document.createElement('a'), { href: url, download: 'refactored.py' });
  a.click();
  URL.revokeObjectURL(url);
});

// ─── metrics ────────────────────────────────────────────────────────────────
function metricCard(name, before, after, digits, lowerIsBetter) {
  const fmt = (v) => Number(v).toFixed(digits);
  const diff = after - before;
  let cls = 'same', txt = 'no change';
  if (Math.abs(diff) > 1e-9) {
    const better = lowerIsBetter ? diff < 0 : diff > 0;
    cls = better ? 'good' : 'bad';
    txt = `${diff > 0 ? '+' : '−'}${Math.abs(diff).toFixed(digits)} ${better ? 'better' : 'worse'}`;
  }
  return `<div class="metric"><div class="name">${name}</div>
    <div class="value">${fmt(before)}<span class="arrow">→</span>${fmt(after)}</div>
    <div class="delta ${cls}">${txt}</div></div>`;
}
function renderMetrics(m) {
  $('metrics').innerHTML = `
    <span class="badge ${m.improved ? 'good' : 'bad'}">${m.improved ? 'Improved' : 'Worse'}</span>
    <div class="metric-grid">
      ${metricCard('Cyclomatic complexity', m.original_complexity, m.refactored_complexity, 1, true)}
      ${metricCard('Lines of code', m.original_loc, m.refactored_loc, 0, true)}
      ${metricCard('Maintainability index', m.original_maintainability, m.refactored_maintainability, 1, false)}
    </div>`;
  $('metrics').hidden = false;
  $('metrics-empty').hidden = true;
}

// ─── refactor (SSE stream) ──────────────────────────────────────────────────
function setStep(node, state) {
  const li = document.querySelector(`#steps li[data-step="${node}"]`);
  if (li) li.className = state;
}
function resetSteps() {
  $('steps').hidden = false;
  document.querySelectorAll('#steps li').forEach((li) => { li.className = ''; });
}

function handleEvent(ev, max) {
  if (ev.event === 'context') {
    setStatus(`Refactoring (attempt 1/${max})...`, 'busy');
    setStep('refactor_node', 'active');
  } else if (ev.event === 'progress') {
    if (ev.node === 'refactor_node') {
      setStep('refactor_node', 'done');
      setStep('verify_node', 'active');
      setStatus(`Verifying & behavior-testing (attempt ${ev.attempt}/${max})...`, 'busy');
    } else if (ev.node === 'verify_node') {
      if (ev.success) {
        setStep('verify_node', 'done');
        setStep('evaluate_node', 'active');
        setStatus('Evaluating quality metrics...', 'busy');
      } else if (ev.attempt < max) {
        setStep('verify_node', '');
        setStep('refactor_node', 'active');
        setStatus(`Attempt ${ev.attempt} failed — retrying (attempt ${ev.attempt + 1}/${max})...`, 'busy');
      } else {
        setStep('verify_node', 'fail');
      }
    } else if (ev.node === 'evaluate_node') {
      setStep('evaluate_node', 'done');
    }
  } else if (ev.event === 'error') {
    throw new Error(ev.detail);
  }
}

async function refactor() {
  showError('');
  const target = $('target-function').value;
  if (!target) { showError('Click Analyze and select a target function first.'); return; }
  const max = Math.min(5, Math.max(1, parseInt($('max-attempts').value, 10) || 3));
  setBusy($('refactor-btn'), true);
  resetSteps();
  setStatus('Retrieving graph context...', 'busy');
  let result = null;
  try {
    const res = await fetch(`${API}/refactor/stream`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ source_code: getCode(), target_function: target, max_attempts: max }),
    });
    if (!res.ok) throw await failure(res);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      for (const part of parts) {
        if (!part.startsWith('data: ')) continue;
        const ev = JSON.parse(part.slice(6));
        if (ev.event === 'result') result = ev.result;
        else handleEvent(ev, max);
      }
    }
    if (!result) throw new Error('Stream ended without a result.');

    if (result.success) {
      renderResult(result);
      if (result.metrics) renderMetrics(result.metrics);
      switchTab('result');
      setStatus(`✅ Done — succeeded on attempt ${result.attempts_used}/${max}`, 'ok');
    } else {
      showError(`Refactoring failed after ${result.attempts_used} attempt(s):\n${result.error || 'unknown error'}`);
      setStatus('Refactoring failed', 'err');
    }
  } catch (e) {
    showError(e.message);
    setStatus('Refactoring failed', 'err');
  } finally {
    setBusy($('refactor-btn'), false);
  }
}

$('analyze-btn').addEventListener('click', analyze);
$('refactor-btn').addEventListener('click', refactor);
loadHealth();
