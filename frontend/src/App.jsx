import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUpRight,
  Check,
  CheckCheck,
  Copy,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  Database,
  FileText,
  Gauge,
  Layers3,
  LogOut,
  Menu,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  UserRound,
  Activity,
  FileStack,
  SlidersHorizontal,
  X,
  Zap,
} from "lucide-react";
import {
  getSession,
  getValidSession,
  signIn,
  signOut,
} from "./api/auth";
import { queryRAG, uploadDocument } from "./api/rag";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const EMPTY_CITATIONS = [];

function formatMs(value) {
  if (value === undefined || value === null) return "—";
  return `${Number(value).toFixed(2)} ms`;
}

function percentage(value) {
  if (value === undefined || value === null) return 0;
  return Math.round(Number(value) * 100);
}

function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [apiOnline, setApiOnline] = useState(false);
  const [expandedChunk, setExpandedChunk] = useState(null);
  const [session, setSession] = useState(() => getSession());
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [mobileNav, setMobileNav] = useState(false);
  const [copied, setCopied] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    let active = true;
    getValidSession()
      .then((current) => {
        if (active) setSession(current);
      })
      .catch(() => {
        if (active) setSession(null);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;

    const checkHealth = async () => {
      try {
        const response = await fetch(`${API_BASE}/health`);
        if (mounted) setApiOnline(response.ok);
      } catch {
        if (mounted) setApiOnline(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleLogin = async (event) => {
    event.preventDefault();
    if (authLoading) return;

    setAuthLoading(true);
    setAuthError("");

    try {
      const nextSession = await signIn(email.trim(), password);
      setSession(nextSession);
      setPassword("");
    } catch (err) {
      setAuthError(err.message || "Sign-in failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    signOut();
    setSession(null);
    setResult(null);
    setSelectedFile(null);
    setUploadMessage("");
    setUploadError("");
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    setUploadMessage("");
    setUploadError("");
  };

  const handleUpload = async () => {
    if (!selectedFile || uploading) return;

    setUploading(true);
    setUploadMessage("");
    setUploadError("");

    try {
      const data = await uploadDocument(selectedFile);
      setUploadMessage(
        data.deduplicated
          ? `${data.filename} is already registered for this pipeline.`
          : `${data.filename} uploaded and queued for ingestion.`
      );
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setUploadError(err.message || "Document upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleAsk = async () => {
    const cleanQuery = query.trim();

    if (!cleanQuery || loading) return;
    if (!session?.access_token) {
      setError("Sign in before querying the enterprise knowledge base.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setExpandedChunk(null);
    setCopied(false);

    try {
      const data = await queryRAG(cleanQuery);
      setResult(data);
      setApiOnline(true);
      window.requestAnimationFrame(() => {
        document.getElementById("results")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    } catch (err) {
      setApiOnline(false);
      setError(err.message || "Unable to process the request.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyAnswer = async () => {
    const answer = result?.answer?.trim();
    if (!answer || !navigator.clipboard) return;

    try {
      await navigator.clipboard.writeText(answer);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleAsk();
    }
  };

  const setSuggestion = (text) => {
    setQuery(text);
    document.getElementById("ask")?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  };

  const metrics = result?.metrics || {};
  const evaluation = result?.evaluation || {};
  const retrieved = result?.retrieved || [];
  const citations = result?.citations ?? EMPTY_CITATIONS;

  const citationMap = useMemo(() => {
    const map = new Map();
    citations.forEach((citation) => {
      if (citation.chunk_id) map.set(citation.chunk_id, citation);
    });
    return map;
  }, [citations]);

  const getCitationForChunk = (chunkId) => citationMap.get(chunkId);
  const toggleChunk = (chunkId) => {
    setExpandedChunk((current) => current === chunkId ? null : chunkId);
  };

  const showEmpty = !loading && !result && !error;

  return (
    <div className="app-shell">
      <div className="grain" aria-hidden="true" />
      <div className="ambient ambient-one" aria-hidden="true" />
      <div className="ambient ambient-two" aria-hidden="true" />

      <header className="topbar">
        <a className="brand" href="#top" aria-label="Enterprise RAG home">
          <span className="brand-mark"><Layers3 size={18} /></span>
          <span className="brand-copy">
            <strong>Enterprise RAG</strong>
            <small>Retrieval intelligence</small>
          </span>
        </a>

        <nav className={`main-nav ${mobileNav ? "open" : ""}`} aria-label="Primary">
          {session ? (
            <>
              <a href="#profile" onClick={() => setMobileNav(false)}>Profile</a>
              <a href="#ask" onClick={() => setMobileNav(false)}>RAG Workbench</a>
              <a href="#results" onClick={() => setMobileNav(false)}>Evidence</a>
            </>
          ) : (
            <>
              <a href="#workspace" onClick={() => setMobileNav(false)}>Platform</a>
              <a href="#system" onClick={() => setMobileNav(false)}>How it works</a>
              <a href="#auth" onClick={() => setMobileNav(false)}>Sign in</a>
            </>
          )}
        </nav>

        <div className="topbar-actions">
          <div className={`api-status ${apiOnline ? "online" : "offline"}`}>
            <span className="status-dot" />
            {apiOnline ? "System online" : "System offline"}
          </div>

          {session ? (
            <div className="profile-actions">
              <a className="profile-trigger" href="#profile" title="Open profile">
                <span>{session.user?.email?.slice(0, 1).toUpperCase() || "U"}</span>
                <UserRound size={14} />
              </a>
              <button className="logout-button" type="button" onClick={handleLogout} title="Sign out">
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <a className="topbar-signin" href="#auth">Sign in <ArrowUpRight size={14} /></a>
          )}
        </div>

        <button
          className="mobile-menu"
          type="button"
          aria-label="Toggle navigation"
          onClick={() => setMobileNav((value) => !value)}
        >
          {mobileNav ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>

      <main id="top" className="main-content">
        {!session ? (
          <section className="public-layout">
            <div className="public-landing">        <section className="hero" id="workspace">
          <div className="hero-copy-block">
            <div className="overline">
              <span className="overline-dot" />
              Tenant-scoped retrieval · grounded generation
            </div>

            <h1>
              Knowledge,
              <br />
              <em>with evidence.</em>
            </h1>

            <p className="hero-copy">
              Ask your enterprise knowledge base a question and trace the
              complete path from retrieval to reranking, generation, citations,
              and evaluation.
            </p>

            <div className="hero-points">
              <span><ShieldCheck size={15} /> Tenant isolated</span>
              <span><Database size={15} /> pgvector retrieval</span>
              <span><Sparkles size={15} /> Citation grounded</span>
            </div>
          </div>

          <aside className="pipeline-card" id="system">
            <div className="pipeline-head">
              <div>
                <span className="eyebrow">HOW IT WORKS</span>
                <h2>From question to evidence</h2>
              </div>
              <span className="pipeline-index">01—04</span>
            </div>

            <div className="pipeline-steps">
              <PipelineStep number="01" icon={<Search size={16} />} title="Retrieve" copy="Search the tenant's indexed knowledge." />
              <PipelineStep number="02" icon={<Layers3 size={16} />} title="Rerank" copy="Cross-encoder scoring refines the evidence." />
              <PipelineStep number="03" icon={<Sparkles size={16} />} title="Generate" copy="Produce an answer constrained by context." />
              <PipelineStep number="04" icon={<Check size={16} />} title="Inspect" copy="Review citations, quality, and latency." last />
            </div>
          </aside>
        </section>


            </div>
            <div className="public-auth">
          <section className="auth-section" id="auth">
            <div className="auth-intro">
              <span className="eyebrow">PRIVATE WORKSPACE</span>
              <h2>Sign in to query your knowledge base.</h2>
              <p>Your session is used to enforce tenant-scoped access.</p>
            </div>
            <form className="auth-card" onSubmit={handleLogin}>
              <label>
                Email
                <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" autoComplete="email" required />
              </label>
              <label>
                Password
                <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" autoComplete="current-password" required />
              </label>
              {authError && <div className="inline-error"><CircleAlert size={15} /> {authError}</div>}
              <button className="primary-button" type="submit" disabled={authLoading}>
                {authLoading ? "Authenticating…" : "Enter workspace"} <ArrowUpRight size={16} />
              </button>
              <div className="auth-footnote"><ShieldCheck size={13} /> Tenant-scoped authentication</div>
            </form>
          </section>
            </div>
          </section>
        ) : (
          <ProfileHeader session={session} onLogout={handleLogout} />
        )}

        {session && (
          <section className="workspace-panel" id="ask">
            <div className="workbench-label">
              <span><Activity size={13} /> RAG WORKBENCH</span>
              <span>Private tenant workspace</span>
            </div>
            <div className="workspace-head">
              <div>
                <span className="eyebrow">QUERY WORKSPACE</span>
                <h2>What do you want to know?</h2>
              </div>
              <div className="signed-in">
                <span className="signed-avatar">
                  {(session.user?.email || "U").slice(0, 1).toUpperCase()}
                </span>
                <span>
                  <small>Authenticated as</small>
                  <strong>{session.user?.email || "authenticated user"}</strong>
                </span>
              </div>
            </div>

            <div className="query-card">
              <div className="query-leading"><Search size={20} /></div>
              <textarea
                rows={2}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your enterprise knowledge…"
                disabled={loading}
                aria-label="Enterprise knowledge query"
              />
              <button
                className="ask-button"
                onClick={handleAsk}
                disabled={!query.trim() || loading}
                aria-label="Run query"
              >
                {loading ? <Gauge className="spin" size={19} /> : <ArrowUpRight size={19} />}
              </button>
            </div>
            <div className="query-hint">
              <span>Enter to run · Shift + Enter for a new line</span>
              <span>{query.length}/500</span>
            </div>

            <div className="suggestions">
              <span>Explore</span>
              <button onClick={() => setSuggestion("Why is job discovery difficult for candidates?")}>
                Why is job discovery difficult?
              </button>
              <button onClick={() => setSuggestion("Why do candidates spend so much time applying for jobs?")}>
                Why do candidates spend so much time applying?
              </button>
              <button onClick={() => setSuggestion("What repetitive tasks do job applicants perform?")}>
                What tasks are repetitive?
              </button>
            </div>

            <div className="ingest-card" id="knowledge-base">
              <div className="ingest-icon"><Upload size={18} /></div>
              <div className="ingest-copy">
                <span className="eyebrow">KNOWLEDGE BASE</span>
                <h3>Add a PDF to this tenant</h3>
                <p>Upload a document and the ingestion worker will queue it for indexing.</p>
              </div>

              <div className="ingest-actions">
                <input
                  ref={fileInputRef}
                  className="file-input"
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={handleFileChange}
                  disabled={uploading}
                />
                <button className="secondary-button" type="button" onClick={handleUpload} disabled={!selectedFile || uploading}>
                  {uploading ? "Uploading…" : "Upload PDF"}
                </button>
              </div>

              {selectedFile && (
                <div className="file-chip">
                  <FileText size={15} />
                  <span>{selectedFile.name}</span>
                  <button type="button" onClick={() => { setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = ""; }} aria-label="Remove selected file">
                    <X size={13} />
                  </button>
                </div>
              )}

              {uploadMessage && <div className="inline-success"><Check size={15} /> {uploadMessage}</div>}
              {uploadError && <div className="inline-error"><CircleAlert size={15} /> {uploadError}</div>}
            </div>
          </section>
        )}

        {error && (
          <div className="error-banner">
            <CircleAlert size={18} />
            <div>
              <strong>Request failed</strong>
              <span>{error}</span>
            </div>
            <button type="button" onClick={() => setError("")} aria-label="Dismiss error"><X size={15} /></button>
          </div>
        )}

        {loading && (
          <section className="state-card loading-card">
            <div className="state-icon"><Sparkles className="spin" size={19} /></div>
            <div>
              <span className="eyebrow">PROCESSING</span>
              <h3>Tracing the retrieval pipeline…</h3>
              <p>Searching, reranking evidence, generating a grounded response, and evaluating the result.</p>
            </div>
          </section>
        )}

        {showEmpty && session && (
          <section className="state-card empty-card">
            <div className="state-icon"><Search size={19} /></div>
            <div>
              <span className="eyebrow">READY WHEN YOU ARE</span>
              <h3>Your evidence workspace is ready.</h3>
              <p>Run a question above to inspect the answer, sources, quality signals, and pipeline timing.</p>
            </div>
            <div className="empty-stat"><strong>04</strong><span>pipeline stages</span></div>
          </section>
        )}

        {result && !loading && (
          <section className="results" id="results">
            <div className="result-heading">
              <div>
                <span className="eyebrow">ANSWER + EVIDENCE</span>
                <h2>Grounded response</h2>
                <p>Everything below came from the same retrieval run.</p>
              </div>
              <div className={`evaluation-badge ${evaluation.passed ? "pass" : "fail"}`}>
                {evaluation.passed ? <Check size={14} /> : <CircleAlert size={14} />}
                {evaluation.passed ? "Evaluation passed" : "Evaluation failed"}
              </div>
            </div>

            <div className="result-layout">
              <article className="answer-panel">
                <div className="answer-meta">
                  <span><Sparkles size={14} /> GENERATED ANSWER</span>
                  <div className="answer-actions">
                    <span>{citations.length} cited sources</span>
                    <button className="copy-button" type="button" onClick={handleCopyAnswer}>
                      {copied ? <CheckCheck size={13} /> : <Copy size={13} />}
                      {copied ? "Copied" : "Copy answer"}
                    </button>
                  </div>
                </div>
                <p className="answer-text">{result.answer || "No answer generated."}</p>
              </article>

              <aside className="quality-panel">
                <div className="quality-head">
                  <div>
                    <span className="eyebrow">QUALITY</span>
                    <h3>Evaluation</h3>
                  </div>
                  <div className="quality-score">{percentage(evaluation.overall_score)}%</div>
                </div>
                <QualityBar label="Citation validity" value={evaluation.citation_score} />
                <QualityBar label="Answer relevance" value={evaluation.relevance_score} />
                <QualityBar label="Evidence support" value={evaluation.support_score} />
              </aside>
            </div>

            <div className="result-grid">
              <section className="surface-panel evidence-surface">
                <PanelHeader eyebrow="EVIDENCE" title="Citations" count={`${citations.length} sources`} />
                <div className="citation-list">
                  {citations.length === 0 && <div className="panel-empty">No citations returned.</div>}
                  {citations.map((citation, index) => {
                    const linkedChunk = retrieved.find((chunk) => chunk.chunk_id === citation.chunk_id);
                    const isExpanded = expandedChunk === citation.chunk_id;

                    return (
                      <div className="citation-wrap" key={`${citation.chunk_id}-${index}`}>
                        <button
                          className="citation-row"
                          type="button"
                          onClick={() => linkedChunk && toggleChunk(citation.chunk_id)}
                          disabled={!linkedChunk}
                        >
                          <span className="citation-number">{citation.source || index + 1}</span>
                          <span className="citation-copy">
                            <strong>{citation.document || "Unknown document"}</strong>
                            <small>Page {citation.page ?? "—"} · {citation.chunk_id}</small>
                          </span>
                          <span className="citation-action">
                            {linkedChunk ? (isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />) : null}
                          </span>
                        </button>
                        {isExpanded && linkedChunk && (
                          <div className="citation-evidence">{linkedChunk.text || "No chunk text available."}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>

              <section className="surface-panel metrics-surface">
                <PanelHeader eyebrow="OBSERVABILITY" title="Pipeline performance" count="LIVE" />
                <div className="metrics-list">
                  <MetricRow icon={<Search size={15} />} label="Retrieval" value={formatMs(metrics.retrieval_ms)} sub={`${result.retrieved_count ?? 0} candidates`} />
                  <MetricRow icon={<Layers3 size={15} />} label="Reranking" value={formatMs(metrics.reranking_ms)} sub={`${result.reranked_count ?? 0} ranked`} />
                  <MetricRow icon={<Zap size={15} />} label="Generation" value={formatMs(metrics.generation_ms)} sub="Answer generation" />
                  <MetricRow icon={<Gauge size={15} />} label="Total latency" value={formatMs(metrics.total_ms)} sub="End-to-end" />
                </div>
              </section>
            </div>

            <section className="surface-panel retrieved-surface">
              <PanelHeader eyebrow="RETRIEVAL TRACE" title="Retrieved evidence" count={`${retrieved.length} chunks`} />
              <div className="chunk-list">
                {retrieved.map((chunk, index) => {
                  const isExpanded = expandedChunk === chunk.chunk_id;
                  const citation = getCitationForChunk(chunk.chunk_id);
                  const score = chunk.rerank_score ?? chunk.score ?? chunk.rrf_score;

                  return (
                    <div className={`chunk-card ${isExpanded ? "expanded" : ""}`} key={chunk.chunk_id || index}>
                      <button className="chunk-row" type="button" onClick={() => toggleChunk(chunk.chunk_id)}>
                        <span className="chunk-index">{String(index + 1).padStart(2, "0")}</span>
                        <span className="chunk-copy">
                          <strong>{chunk.chunk_id || `chunk-${index + 1}`}</strong>
                          <small>{chunk.source || chunk.document_id || "Unknown document"} · Page {chunk.page ?? "—"}</small>
                        </span>
                        <span className="chunk-score">{score !== undefined ? Number(score).toFixed(3) : "—"} {isExpanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}</span>
                      </button>
                      {isExpanded && (
                        <div className="chunk-detail">
                          <p>{chunk.text || "No retrieved text available."}</p>
                          {citation && <span>Citation · Source {citation.source} · Page {citation.page}</span>}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          </section>
        )}
      </main>

      <footer className="footer">
        <span>ENTERPRISE RAG / RETRIEVAL INTELLIGENCE</span>
        <span><span className="status-dot" /> pgvector · reranking · grounded generation</span>
      </footer>
    </div>
  );
}

function ProfileHeader({ session, onLogout }) {
  const email = session.user?.email || "authenticated user";

  return (
    <section className="profile-shell" id="profile">
      <div className="profile-main">
        <div className="profile-avatar"><UserRound size={28} /></div>
        <div className="profile-copy">
          <span className="eyebrow">PERSONAL WORKSPACE</span>
          <h1>Welcome back.</h1>
          <p>{email}</p>
        </div>
        <div className="profile-status"><span className="status-dot online-dot" /> Workspace active</div>
      </div>

      <div className="profile-actions-grid">
        <a className="profile-card active" href="#ask">
          <span className="profile-card-icon"><Search size={17} /></span>
          <span><strong>RAG Workbench</strong><small>Ask, retrieve, rerank, inspect</small></span>
          <ChevronRight size={15} />
        </a>
        <a className="profile-card" href="#knowledge-base">
          <span className="profile-card-icon"><FileStack size={17} /></span>
          <span><strong>Knowledge Base</strong><small>Upload and index PDF sources</small></span>
          <ChevronRight size={15} />
        </a>
        <a className="profile-card" href="#results">
          <span className="profile-card-icon"><Activity size={17} /></span>
          <span><strong>Evidence & Metrics</strong><small>Review citations and latency</small></span>
          <ChevronRight size={15} />
        </a>
        <button className="profile-card" type="button" onClick={onLogout}>
          <span className="profile-card-icon"><SlidersHorizontal size={17} /></span>
          <span><strong>Session</strong><small>Sign out of this workspace</small></span>
          <LogOut size={15} />
        </button>
      </div>
    </section>
  );
}

function PipelineStep({ number, icon, title, copy, last }) {
  return (
    <div className={`pipeline-step ${last ? "last" : ""}`}>
      <span className="step-number">{number}</span>
      <span className="step-icon">{icon}</span>
      <div>
        <strong>{title}</strong>
        <p>{copy}</p>
      </div>
    </div>
  );
}

function PanelHeader({ eyebrow, title, count }) {
  return (
    <div className="panel-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h3>{title}</h3>
      </div>
      {count && <span className="panel-count">{count}</span>}
    </div>
  );
}

function MetricRow({ icon, label, value, sub }) {
  return (
    <div className="metric-row">
      <span className="metric-icon">{icon}</span>
      <span className="metric-copy"><strong>{label}</strong><small>{sub}</small></span>
      <span className="metric-value">{value}</span>
    </div>
  );
}

function QualityBar({ label, value }) {
  const percent = percentage(value);
  return (
    <div className="quality-bar">
      <div><span>{label}</span><strong>{percent}%</strong></div>
      <span className="bar-track"><span className="bar-fill" style={{ width: `${percent}%` }} /></span>
    </div>
  );
}

export default App;
