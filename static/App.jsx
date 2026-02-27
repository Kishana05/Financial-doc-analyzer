const { useState, useEffect, useCallback, useRef } = React;

// ─── Lucide Icon Helper ──────────────────────────────────────────────────────
const Icon = ({ name, size = 18, className = '' }) => {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current && window.lucide) {
      ref.current.innerHTML = '';
      const el = document.createElement('i');
      el.setAttribute('data-lucide', name);
      el.style.width = size + 'px';
      el.style.height = size + 'px';
      ref.current.appendChild(el);
      window.lucide.createIcons({ nodes: [el] });
    }
  }, [name, size]);
  return <span ref={ref} className={`inline-flex items-center justify-center ${className}`} />;
};

// ─── Constants ───────────────────────────────────────────────────────────────
const API = 'http://localhost:8000';
const POLL_INTERVAL = 3000;

const STATUS_CONFIG = {
  PENDING: { color: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/30', icon: 'clock', label: 'Pending' },
  PROCESSING: { color: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/30', icon: 'loader-2', label: 'Processing' },
  COMPLETED: { color: 'text-emerald-400', bg: 'bg-emerald-400/10', border: 'border-emerald-400/30', icon: 'check-circle-2', label: 'Completed' },
  FAILED: { color: 'text-red-400', bg: 'bg-red-400/10', border: 'border-red-400/30', icon: 'x-circle', label: 'Failed' },
};

// ─── Utilities ────────────────────────────────────────────────────────────────
function formatBytes(b) {
  if (!b) return '0 B';
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
  return (b / 1048576).toFixed(2) + ' MB';
}

function formatDate(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function timeAgo(iso) {
  if (!iso) return '-';
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 60) return diff + 's ago';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
}

// ─── Status Badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status, size = 'sm' }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.PENDING;
  const spinning = status === 'PROCESSING';
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm';
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border font-medium ${textSize} ${cfg.color} ${cfg.bg} ${cfg.border}`}>
      <Icon name={cfg.icon} size={size === 'sm' ? 12 : 14} className={spinning ? 'spin' : ''} />
      {cfg.label}
    </span>
  );
}

// ─── Progress Bar ─────────────────────────────────────────────────────────────
function ProgressBar({ status }) {
  const widths = { PENDING: 'w-1/4', PROCESSING: 'w-2/3', COMPLETED: 'w-full', FAILED: 'w-2/3' };
  const colors = { PENDING: 'progress-bar', PROCESSING: 'progress-bar', COMPLETED: 'bg-emerald-500', FAILED: 'bg-red-500' };
  return (
    <div className="w-full bg-navy-800 rounded-full h-1.5 overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-700 ${widths[status] || 'w-0'} ${colors[status] || 'progress-bar'}`} />
    </div>
  );
}

// ─── Markdown Result Renderer ─────────────────────────────────────────────────
function MarkdownResult({ text }) {
  const html = React.useMemo(() => {
    if (!text) return '';
    try { return window.marked ? window.marked.parse(text) : text; }
    catch { return text; }
  }, [text]);
  return (
    <div
      className="result-content prose max-w-none text-sm leading-relaxed"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

// ─── Upload Zone ──────────────────────────────────────────────────────────────
function UploadZone({ onSubmit, loading }) {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState('');
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const acceptFile = (f) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are accepted.');
      return;
    }
    setError('');
    setFile(f);
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    acceptFile(f);
  }, []);

  const onDragOver = (e) => { e.preventDefault(); setDrag(true); };
  const onDragLeave = () => setDrag(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!file) { setError('Please select a PDF file first.'); return; }
    onSubmit(file, query.trim());
  };

  return (
    <div className="slide-up">
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Drop zone */}
        <div
          onClick={() => inputRef.current?.click()}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          className={`
            relative cursor-pointer rounded-2xl border-2 border-dashed p-10
            transition-all duration-200 text-center group
            ${drag ? 'drop-zone-active' : 'border-navy-700 hover:border-blue-500/50 hover:bg-blue-500/5'}
            ${file ? 'border-emerald-500/50 bg-emerald-500/5' : ''}
          `}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,application/pdf"
            className="hidden"
            onChange={(e) => acceptFile(e.target.files[0])}
          />
          {file ? (
            <div className="fade-in flex flex-col items-center gap-3">
              <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
                <Icon name="file-check-2" size={28} className="text-emerald-400" />
              </div>
              <div>
                <p className="text-emerald-300 font-semibold text-base">{file.name}</p>
                <p className="text-slate-500 text-sm mt-0.5">{formatBytes(file.size)} · PDF</p>
              </div>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setFile(null); }}
                className="text-xs text-slate-500 hover:text-red-400 transition-colors mt-1 flex items-center gap-1"
              >
                <Icon name="x" size={12} /> Remove
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
                <Icon name="upload-cloud" size={28} className="text-blue-400" />
              </div>
              <div>
                <p className="text-white font-semibold text-base">Drop your PDF here</p>
                <p className="text-slate-500 text-sm mt-1">or <span className="text-blue-400 hover:text-blue-300">browse files</span></p>
              </div>
              <p className="text-slate-600 text-xs">Supports PDF files · Annual reports, 10-Ks, earnings releases</p>
            </div>
          )}
        </div>

        {/* Query input */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-400 flex items-center gap-2">
            <Icon name="message-square" size={14} className="text-blue-400" />
            Analysis Query <span className="text-slate-600 font-normal">(optional)</span>
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. What is the revenue growth trend and free cash flow outlook?"
            rows={3}
            className="w-full bg-navy-800 border border-navy-700 rounded-xl px-4 py-3 text-sm text-slate-200
                       placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1
                       focus:ring-blue-500/30 resize-none transition-colors"
          />
        </div>

        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 fade-in">
            <Icon name="alert-circle" size={16} />
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !file}
          className="w-full py-3.5 rounded-xl font-semibold text-sm transition-all duration-200
                     bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-40 disabled:cursor-not-allowed
                     flex items-center justify-center gap-2 glow-blue"
        >
          {loading ? (
            <>
              <Icon name="loader-2" size={18} className="spin" />
              Uploading…
            </>
          ) : (
            <>
              <Icon name="brain-circuit" size={18} />
              Analyze Document
            </>
          )}
        </button>
      </form>
    </div>
  );
}

// ─── Job Status Card ──────────────────────────────────────────────────────────
function JobStatusCard({ job, onDismiss }) {
  if (!job) return null;
  const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.PENDING;
  return (
    <div className={`slide-up rounded-2xl border p-5 space-y-4 ${cfg.bg} ${cfg.border}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${cfg.bg} border ${cfg.border}`}>
            <Icon name={cfg.icon} size={18} className={`${cfg.color} ${job.status === 'PROCESSING' ? 'spin' : ''}`} />
          </div>
          <div>
            <p className="text-white font-semibold text-sm">{job.filename || 'Document'}</p>
            <p className="text-slate-500 text-xs font-mono mt-0.5">{job.job_id?.slice(0, 8)}…</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={job.status} />
          {(job.status === 'FAILED') && (
            <button onClick={onDismiss} className="text-slate-500 hover:text-slate-300 transition-colors">
              <Icon name="x" size={16} />
            </button>
          )}
        </div>
      </div>

      <ProgressBar status={job.status} />

      {job.status === 'PENDING' && (
        <p className="text-slate-400 text-xs flex items-center gap-1.5">
          <Icon name="hourglass" size={12} className="text-amber-400" />
          Queued — the AI pipeline will start shortly…
        </p>
      )}
      {job.status === 'PROCESSING' && (
        <p className="text-slate-400 text-xs flex items-center gap-1.5">
          <Icon name="sparkles" size={12} className="text-blue-400" />
          Multi-agent analysis in progress — this typically takes 1–3 minutes…
        </p>
      )}
      {job.status === 'FAILED' && job.error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
          <p className="text-red-300 text-xs font-semibold mb-1 flex items-center gap-1.5">
            <Icon name="alert-triangle" size={12} /> Error Details
          </p>
          <p className="text-red-400 text-xs font-mono leading-relaxed">{job.error}</p>
        </div>
      )}
    </div>
  );
}

// ─── Results Panel ────────────────────────────────────────────────────────────
function ResultsPanel({ job }) {
  if (!job || job.status !== 'COMPLETED' || !job.result) return null;
  return (
    <div className="slide-up space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
            <Icon name="file-bar-chart-2" size={18} className="text-emerald-400" />
          </div>
          <div>
            <p className="text-white font-semibold text-sm">Analysis Report</p>
            <p className="text-slate-500 text-xs mt-0.5">{formatDate(job.created_at)}</p>
          </div>
        </div>
        <button
          onClick={() => {
            const blob = new Blob([job.result], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `analysis-${job.job_id?.slice(0, 8)}.md`;
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="text-xs text-slate-400 hover:text-blue-400 transition-colors flex items-center gap-1.5
                     bg-navy-800 border border-navy-700 hover:border-blue-500/30 rounded-lg px-3 py-1.5"
        >
          <Icon name="download" size={13} /> Export
        </button>
      </div>

      {/* Query echo */}
      {job.query && (
        <div className="bg-blue-500/8 border border-blue-500/20 rounded-xl px-4 py-3 flex items-start gap-2">
          <Icon name="search" size={14} className="text-blue-400 mt-0.5 shrink-0" />
          <p className="text-blue-200 text-xs leading-relaxed">{job.query}</p>
        </div>
      )}

      {/* Report */}
      <div className="bg-navy-900/60 border border-navy-700 rounded-2xl p-6 glow-blue">
        <MarkdownResult text={job.result} />
      </div>
    </div>
  );
}



// ─── Main App ─────────────────────────────────────────────────────────────────
function App() {
  const [currentJob, setCurrentJob] = useState(null);   // {job_id, status, filename, result, error, ...}
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const pollRef = useRef(null);

  // ── Polling ──
  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  const pollJob = useCallback(async (jobId) => {
    try {
      const res = await fetch(`${API}/results/${jobId}`);
      if (!res.ok) return;
      const data = await res.json();
      setCurrentJob(data);
      if (data.status === 'COMPLETED' || data.status === 'FAILED') {
        stopPolling();
      }
    } catch (e) {
      console.error('Poll error:', e);
    }
  }, []);

  const startPolling = useCallback((jobId) => {
    stopPolling();
    pollJob(jobId);
    pollRef.current = setInterval(() => pollJob(jobId), POLL_INTERVAL);
  }, [pollJob]);

  useEffect(() => () => stopPolling(), []);

  // ── Upload & Submit ──
  const handleSubmit = async (file, query) => {
    setUploading(true);
    setUploadError('');
    setCurrentJob(null);
    stopPolling();
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('query', query || 'Provide a comprehensive analysis of this financial document.');
      const res = await fetch(`${API}/analyze`, { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      setCurrentJob({ job_id: data.job_id, status: 'PENDING', filename: file.name });
      startPolling(data.job_id);
    } catch (e) {
      setUploadError(e.message);
    } finally {
      setUploading(false);
    }
  };



  return (
    <div className="min-h-screen bg-navy-950 text-white font-sans flex flex-col">
      {/* ── Top Nav ── */}
      <header className="border-b border-navy-800 bg-navy-950/80 glass sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center glow-blue">
              <Icon name="trending-up" size={16} className="text-white" />
            </div>
            <div>
              <span className="font-bold text-white text-base tracking-tight">FinSight</span>
              <span className="text-blue-400 font-bold text-base tracking-tight"> AI</span>
            </div>
            <span className="hidden sm:block text-slate-600 text-xs ml-2 border-l border-navy-800 pl-3">
              Financial Document Analyzer
            </span>
          </div>
          <a
            href="/docs"
            target="_blank"
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            <Icon name="book-open" size={13} /> API Docs
          </a>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="max-w-3xl mx-auto w-full px-4 py-6">
        <main className="space-y-6">

          {/* Upload card */}
          <div className="bg-navy-900/50 glass border border-navy-800 rounded-2xl p-6 glow-blue">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-9 h-9 rounded-xl bg-blue-600/15 border border-blue-500/30 flex items-center justify-center">
                <Icon name="upload" size={18} className="text-blue-400" />
              </div>
              <div>
                <h2 className="text-white font-semibold text-sm">Upload Financial Document</h2>
                <p className="text-slate-500 text-xs mt-0.5">Annual reports, 10-Ks, earnings releases, balance sheets</p>
              </div>
            </div>
            <UploadZone onSubmit={handleSubmit} loading={uploading} />
            {uploadError && (
              <div className="mt-4 flex items-start gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 fade-in">
                <Icon name="alert-circle" size={14} className="shrink-0 mt-0.5" />
                <span>{uploadError}</span>
              </div>
            )}
          </div>

          {/* Job status card */}
          {currentJob && currentJob.status !== 'COMPLETED' && (
            <JobStatusCard
              job={currentJob}
              onDismiss={() => setCurrentJob(null)}
            />
          )}

          {/* Results */}
          {currentJob && currentJob.status === 'COMPLETED' && (
            <div className="bg-navy-900/50 glass border border-navy-800 rounded-2xl p-6">
              <ResultsPanel job={currentJob} />
            </div>
          )}

          {/* Empty state */}
          {!currentJob && (
            <div className="fade-in flex flex-col items-center justify-center py-16 gap-4 text-center">
              <div className="relative">
                <div className="w-20 h-20 rounded-2xl bg-navy-900 border border-navy-800 flex items-center justify-center">
                  <Icon name="bar-chart-3" size={36} className="text-navy-700" />
                </div>
                <div className="absolute -top-1 -right-1 w-6 h-6 rounded-lg bg-blue-600 border-2 border-navy-950 flex items-center justify-center">
                  <Icon name="sparkles" size={12} className="text-white" />
                </div>
              </div>
              <div>
                <p className="text-slate-500 font-medium text-sm">Ready to analyze</p>
                <p className="text-slate-700 text-xs mt-1 max-w-xs">
                  Upload a PDF financial document above to get AI-powered insights, risk assessment, and investment analysis.
                </p>
              </div>
              <div className="flex items-center gap-4 mt-2">
                {['Revenue Trends', 'Risk Profile', 'Investment Case'].map(tag => (
                  <span key={tag} className="text-xs text-slate-700 border border-navy-800 rounded-full px-3 py-1">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className="border-t border-navy-900 py-4 px-4 text-center">
        <p className="text-slate-700 text-xs">
          FinSight AI · Powered by <span className="text-blue-600">GPT-4o-mini</span> · CrewAI multi-agent pipeline
        </p>
      </footer>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
