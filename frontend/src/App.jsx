import { useEffect, useMemo, useRef, useState } from "react";
import {
  getSession,
  signIn,
  signOut,
} from "./api/auth";
import { uploadDocument } from "./api/rag";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function Icon({ name, size = 18 }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  };

  const paths = {
    search: (
      <>
        <circle cx="11" cy="11" r="6.5" />
        <path d="m16 16 4 4" />
      </>
    ),
    arrow: (
      <>
        <path d="M5 12h14" />
        <path d="m13 6 6 6-6 6" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    alert: (
      <>
        <path d="M12 3 22 20H2L12 3Z" />
        <path d="M12 9v5" />
        <path d="M12 17h.01" />
      </>
    ),
    file: (
      <>
        <path d="M6 3h8l4 4v14H6z" />
        <path d="M14 3v5h5" />
        <path d="M9 13h6" />
        <path d="M9 17h6" />
      </>
    ),
    database: (
      <>
        <ellipse cx="12" cy="5" rx="7" ry="3" />
        <path d="M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5" />
        <path d="M5 12v7c0 1.7 3.1 3 7 3s7-1.3 7-3v-7" />
      </>
    ),
    layers: (
      <>
        <path d="m12 3 9 5-9 5-9-5 9-5Z" />
        <path d="m3 12 9 5 9-5" />
        <path d="m3 16 9 5 9-5" />
      </>
    ),
    bolt: <path d="m13 2-9 12h7l-1 8 9-12h-7l1-8Z" />,
    gauge: (
      <>
        <path d="M4 18a8 8 0 1 1 16 0" />
        <path d="M12 14l4-4" />
      </>
    ),
    chevron: <path d="m6 9 6 6 6-6" />,
    spark: (
      <>
        <path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Z" />
        <path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z" />
      </>
    ),
  };

  return <svg {...common}>{paths[name] || paths.spark}</svg>;
}

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
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");
  const fileInputRef = useRef(null);

  // ---------------------------------------------------------
  // Auth session
  // ---------------------------------------------------------

  useEffect(() => {
    setSession(getSession());
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
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      setUploadError(err.message || "Document upload failed.");
    } finally {
      setUploading(false);
    }
  };

  // ---------------------------------------------------------
  // API health check
  // ---------------------------------------------------------

  useEffect(() => {
    let mounted = true;

    const checkHealth = async () => {
      try {
        const response = await fetch(`${API_BASE}/health`);

        if (mounted) {
          setApiOnline(response.ok);
        }
      } catch {
        if (mounted) {
          setApiOnline(false);
        }
      }
    };

    checkHealth();

    const interval = setInterval(checkHealth, 10000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  // ---------------------------------------------------------
  // Query execution
  // ---------------------------------------------------------

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

    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          query: cleanQuery,
        }),
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      const data = await response.json();

      setResult(data);
      setApiOnline(true);
    } catch (err) {
      console.error(err);
      setApiOnline(false);
      setError(
        "Unable to connect to the Enterprise RAG API. Make sure the backend is running on port 8000."
      );
    } finally {
      setLoading(false);
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
  };

  // ---------------------------------------------------------
  // Result helpers
  // ---------------------------------------------------------

  const metrics = result?.metrics || {};
  const evaluation = result?.evaluation || {};

  const retrieved = result?.retrieved || [];
  const citations = result?.citations || [];

  const citationMap = useMemo(() => {
    const map = new Map();

    citations.forEach((citation) => {
      if (citation.chunk_id) {
        map.set(citation.chunk_id, citation);
      }
    });

    return map;
  }, [citations]);

  const getCitationForChunk = (chunkId) => {
    return citationMap.get(chunkId);
  };

  const toggleChunk = (chunkId) => {
    setExpandedChunk((current) =>
      current === chunkId ? null : chunkId
    );
  };

  // ---------------------------------------------------------
  // Empty state
  // ---------------------------------------------------------

  const showEmpty = !loading && !result && !error;

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      {/* =====================================================
          TOP BAR
      ===================================================== */}

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Icon name="layers" size={17} />
          </div>

          <div>
            <div className="brand-name">Enterprise RAG</div>
            <div className="brand-caption">
              Retrieval Intelligence Platform
            </div>
          </div>
        </div>

        <div
          className={`status-pill ${
            apiOnline ? "online" : "offline"
          }`}
        >
          <span className="status-dot" />

          {apiOnline ? "API ONLINE" : "API OFFLINE"}
        </div>
      </header>

      <main className="main-content">
        {/* =================================================
            HERO
        ================================================= */}

        <section className="hero">
          <div className="eyebrow">
            <span>
              <Icon name="database" size={12} />
              TENANT-SCOPED PGVECTOR
            </span>

            <span>
              <Icon name="layers" size={12} />
              CROSS-ENCODER RERANKING
            </span>

            <span>
              <Icon name="spark" size={12} />
              GROUNDED GENERATION
            </span>
          </div>

          <h1>
            Enterprise <span>RAG</span>
          </h1>

          <p className="hero-copy">
            Ask questions across your enterprise knowledge base and
            inspect exactly how the answer was retrieved, ranked,
            generated, and evaluated.
          </p>

          {!session ? (
            <form className="auth-panel" onSubmit={handleLogin}>
              <div>
                <div className="section-kicker">AUTHENTICATION</div>
                <h3>Sign in to Enterprise RAG</h3>
                <p>Use your Supabase account to access tenant-scoped retrieval.</p>
              </div>

              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="Email"
                autoComplete="email"
                required
              />

              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Password"
                autoComplete="current-password"
                required
              />

              {authError && <div className="auth-error">{authError}</div>}

              <button className="auth-button" type="submit" disabled={authLoading}>
                {authLoading ? "Signing in..." : "Sign in"}
              </button>
            </form>
          ) : (
            <div className="session-bar">
              <span>Signed in as {session.user?.email || "authenticated user"}</span>
              <button type="button" onClick={handleLogout}>Sign out</button>
            </div>
          )}

          {/* =================================================
              DOCUMENT INGESTION
          ================================================= */}

          {session && (
            <div className="upload-panel">
              <div className="upload-copy">
                <div className="section-kicker">KNOWLEDGE BASE</div>
                <h3>Upload a PDF</h3>
                <p>
                  Documents are stored in your tenant, queued for the Railway
                  ingestion worker, then indexed for pgvector retrieval.
                </p>
              </div>

              <div className="upload-controls">
                <input
                  ref={fileInputRef}
                  className="file-input"
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={handleFileChange}
                  disabled={uploading}
                />

                <button
                  className="upload-button"
                  type="button"
                  onClick={handleUpload}
                  disabled={!selectedFile || uploading}
                >
                  {uploading ? "Uploading..." : "Upload document"}
                </button>
              </div>

              {selectedFile && (
                <div className="upload-file">
                  <Icon name="file" size={15} />
                  <span>{selectedFile.name}</span>
                </div>
              )}

              {uploadMessage && (
                <div className="upload-success">
                  <Icon name="check" size={15} />
                  <span>{uploadMessage}</span>
                </div>
              )}

              {uploadError && (
                <div className="upload-error">
                  <Icon name="alert" size={15} />
                  <span>{uploadError}</span>
                </div>
              )}

              <div className="upload-note">
                PDF only · up to 20 MB · ingestion runs asynchronously
              </div>
            </div>
          )}

          {/* =================================================
              QUERY BOX
          ================================================= */}

          <div className="query-box">
            <div className="query-icon">
              <Icon name="search" size={19} />
            </div>

            <textarea
              rows={1}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask your enterprise knowledge..."
              disabled={loading || !session}
            />

            <button
              className="submit-button"
              onClick={handleAsk}
              disabled={!query.trim() || loading}
              aria-label="Ask"
            >
              {loading ? (
                <span className="spin">
                  <Icon name="gauge" size={18} />
                </span>
              ) : (
                <Icon name="arrow" size={18} />
              )}
            </button>
          </div>

          <div className="suggestions">
            <span>Try:</span>

            <button
              onClick={() =>
                setSuggestion(
                  "Why is job discovery difficult for candidates?"
                )
              }
            >
              Why is job discovery difficult for candidates?
            </button>

            <button
              onClick={() =>
                setSuggestion(
                  "Why do candidates spend so much time applying for jobs?"
                )
              }
            >
              Why do candidates spend so much time applying?
            </button>

            <button
              onClick={() =>
                setSuggestion(
                  "What repetitive tasks do job applicants perform?"
                )
              }
            >
              What repetitive tasks do applicants perform?
            </button>
          </div>
        </section>

        {/* =================================================
            ERROR
        ================================================= */}

        {error && (
          <div className="error-panel">
            <Icon name="alert" size={19} />

            <div>
              <strong>Request failed</strong>
              <p>{error}</p>
            </div>
          </div>
        )}

        {/* =================================================
            LOADING
        ================================================= */}

        {loading && (
          <section className="loading-state">
            <div className="loading-icon spin">
              <Icon name="layers" size={20} />
            </div>

            <h3>Running retrieval pipeline</h3>

            <p>
              Searching the knowledge base, reranking evidence,
              generating a grounded response, and evaluating the
              result.
            </p>
          </section>
        )}

        {/* =================================================
            EMPTY
        ================================================= */}

        {showEmpty && (
          <section className="empty-state">
            <div className="empty-icon">
              <Icon name="search" size={21} />
            </div>

            <h3>Ask your enterprise knowledge base</h3>

            <p>
              Enter a question above to inspect a complete RAG
              pipeline with retrieved evidence, citations,
              evaluation scores, and latency metrics.
            </p>
          </section>
        )}

        {/* =================================================
            RESULTS
        ================================================= */}

        {result && !loading && (
          <section className="results">
            {/* -------------------------------------------------
                RESULT HEADER
            ------------------------------------------------- */}

            <div className="section-heading">
              <div>
                <div className="section-kicker">RESULT</div>

                <h2>Grounded response</h2>
              </div>

              <div
                className={`pass-badge ${
                  evaluation.passed ? "pass" : "fail"
                }`}
              >
                <Icon
                  name={evaluation.passed ? "check" : "alert"}
                  size={13}
                />

                {evaluation.passed
                  ? "Evaluation passed"
                  : "Evaluation failed"}
              </div>
            </div>

            {/* -------------------------------------------------
                ANSWER
            ------------------------------------------------- */}

            <div className="answer-card">
              <div className="answer-label">
                <Icon name="spark" size={13} />
                GENERATED ANSWER
              </div>

              <div className="answer-text">
                {result.answer || "No answer generated."}
              </div>
            </div>

            {/* -------------------------------------------------
                CITATIONS + QUALITY
            ------------------------------------------------- */}

            <div className="dashboard-grid">
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <div className="section-kicker">EVIDENCE</div>
                    <h3>Citations</h3>
                  </div>

                  <div className="count-badge">
                    {citations.length} sources
                  </div>
                </div>

                <div className="citation-list">
                  {citations.length === 0 && (
                    <div className="empty-state">
                      <p>No citations returned.</p>
                    </div>
                  )}

                  {citations.map((citation, index) => {
                    const linkedChunk = retrieved.find(
                      (chunk) =>
                        chunk.chunk_id === citation.chunk_id
                    );

                    const isExpanded =
                      expandedChunk === citation.chunk_id;

                    return (
                      <div key={`${citation.chunk_id}-${index}`}>
                        <button
                          className="citation-card"
                          onClick={() =>
                            linkedChunk &&
                            toggleChunk(citation.chunk_id)
                          }
                          disabled={!linkedChunk}
                        >
                          <div className="source-number">
                            {citation.source || index + 1}
                          </div>

                          <div className="citation-info">
                            <strong>
                              {citation.document ||
                                "Unknown document"}
                            </strong>

                            <span>
                              Page {citation.page ?? "—"} •{" "}
                              {citation.chunk_id}
                            </span>

                            {linkedChunk && (
                              <small>
                                {isExpanded
                                  ? "Hide retrieved evidence"
                                  : "View retrieved evidence →"}
                              </small>
                            )}
                          </div>

                          <Icon
                            name={
                              isExpanded
                                ? "chevron"
                                : "arrow"
                            }
                            size={15}
                          />
                        </button>

                        {isExpanded && linkedChunk && (
                          <div className="chunk-text">
                            {linkedChunk.text ||
                              "No chunk text available."}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="panel">
                <div className="panel-header">
                  <div>
                    <div className="section-kicker">QUALITY</div>
                    <h3>Evaluation</h3>
                  </div>

                  <div className="score-ring">
                    {percentage(evaluation.overall_score)}%
                  </div>
                </div>

                <div className="quality-bars">
                  <QualityBar
                    label="Citation validity"
                    value={evaluation.citation_score}
                  />

                  <QualityBar
                    label="Answer relevance"
                    value={evaluation.relevance_score}
                  />

                  <QualityBar
                    label="Evidence support"
                    value={evaluation.support_score}
                  />
                </div>
              </div>
            </div>

            {/* -------------------------------------------------
                PIPELINE METRICS
            ------------------------------------------------- */}

            <div className="panel metrics-panel">
              <div className="panel-header">
                <div>
                  <div className="section-kicker">
                    OBSERVABILITY
                  </div>

                  <h3>Pipeline performance</h3>
                </div>

                <div className="live-label">
                  <span className="status-dot" />
                  LIVE RESULT
                </div>
              </div>

              <div className="metrics-grid">
                <MetricCard
                  icon="search"
                  label="Retrieval"
                  value={formatMs(metrics.retrieval_ms)}
                  sub={`${result.retrieved_count ?? 0} candidates`}
                />

                <MetricCard
                  icon="layers"
                  label="Reranking"
                  value={formatMs(metrics.reranking_ms)}
                  sub={`${result.reranked_count ?? 0} documents`}
                />

                <MetricCard
                  icon="bolt"
                  label="Generation"
                  value={formatMs(metrics.generation_ms)}
                  sub="Answer generation"
                />

                <MetricCard
                  icon="gauge"
                  label="Total latency"
                  value={formatMs(metrics.total_ms)}
                  sub="End-to-end"
                />
              </div>
            </div>

            {/* -------------------------------------------------
                RETRIEVED EVIDENCE
            ------------------------------------------------- */}

            <div className="panel evidence-panel">
              <div className="panel-header">
                <div>
                  <div className="section-kicker">
                    RETRIEVAL
                  </div>

                  <h3>Retrieved evidence</h3>
                </div>

                <div className="count-badge">
                  {retrieved.length} chunks
                </div>
              </div>

              <div className="chunk-list">
                {retrieved.map((chunk, index) => {
                  const isExpanded =
                    expandedChunk === chunk.chunk_id;

                  const citation =
                    getCitationForChunk(chunk.chunk_id);

                  const score =
                    chunk.rerank_score ??
                    chunk.score ??
                    chunk.rrf_score;

                  return (
                    <div
                      className={`chunk-card ${
                        isExpanded ? "expanded" : ""
                      }`}
                      key={chunk.chunk_id || index}
                    >
                      <button
                        className="chunk-head"
                        onClick={() =>
                          toggleChunk(chunk.chunk_id)
                        }
                      >
                        <div className="chunk-rank">
                          {index + 1}
                        </div>

                        <div className="chunk-main">
                          <strong>
                            {chunk.chunk_id ||
                              `chunk-${index + 1}`}
                          </strong>

                          <span>
                            {chunk.source ||
                              chunk.document_id ||
                              "Unknown document"}{" "}
                            • Page {chunk.page ?? "—"}
                          </span>
                        </div>

                        <div className="chunk-score">
                          {score !== undefined
                            ? Number(score).toFixed(3)
                            : "—"}

                          <Icon
                            name={
                              isExpanded
                                ? "chevron"
                                : "arrow"
                            }
                            size={13}
                          />
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="chunk-text">
                          {chunk.text ||
                            "No retrieved text available."}

                          {citation && (
                            <div style={{ marginTop: 12 }}>
                              Citation: Source{" "}
                              {citation.source} • Page{" "}
                              {citation.page}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        )}
      </main>

      {/* =====================================================
          FOOTER
      ===================================================== */}

      <footer className="footer">
        <span>ENTERPRISE RAG • RETRIEVAL INTELLIGENCE</span>

        <span>
          <span className="status-dot" />
          pgvector retrieval · Reranking · Grounded generation
        </span>
      </footer>
    </div>
  );
}

function MetricCard({ icon, label, value, sub }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">
        <Icon name={icon} size={16} />
      </div>

      <div>
        <div className="metric-label">{label}</div>
        <div className="metric-value">{value}</div>
        <div className="metric-sub">{sub}</div>
      </div>
    </div>
  );
}

function QualityBar({ label, value }) {
  const percent = percentage(value);

  return (
    <div>
      <div className="quality-top">
        <span>{label}</span>
        <strong>{percent}%</strong>
      </div>

      <div className="bar-track">
        <div
          className="bar-fill"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

export default App;