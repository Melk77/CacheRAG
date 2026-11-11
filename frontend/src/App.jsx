import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  Copy,
  Database,
  FileText,
  LoaderCircle,
  Menu,
  MessageSquare,
  Moon,
  MoreHorizontal,
  Plus,
  Search,
  Send,
  Settings,
  Sparkles,
  Sun,
  Trash2,
  Upload,
  X,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./App.css";

async function api(path, options = {}) {
  const response = await fetch(path, options);

  if (response.status === 204) return null;

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail || data.message || `Request failed (${response.status})`,
    );
  }

  return data;
}

const navigation = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "collections", label: "Collections", icon: Database },
  { id: "documents", label: "Documents", icon: FileText },
  { id: "performance", label: "Performance", icon: Activity },
  { id: "settings", label: "Settings", icon: Settings },
];

const suggestions = [
  "Summarize the key concepts in my documents",
  "What are the most important topics?",
  "Compare the main ideas across my files",
];

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
}

function formatDuration(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${Number(value).toFixed(1)} ms`;
}

/* Renders basic Markdown bold formatting and preserves line breaks. */
function renderMessageText(content) {
  const lines = String(content ?? "").split("\n");

  return lines.map((line, lineIndex) => {
    const parts = line.split(/(\*\*.+?\*\*)/g);

    return (
      <span className="message-line" key={lineIndex}>
        {parts.map((part, index) => {
          if (
            part.startsWith("**") &&
            part.endsWith("**") &&
            part.length >= 4
          ) {
            return <strong key={index}>{part.slice(2, -2)}</strong>;
          }

          return <span key={index}>{part}</span>;
        })}
      </span>
    );
  });
}

function App() {
  const [page, setPage] = useState("chat");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenu, setMobileMenu] = useState(false);

  const [dark, setDark] = useState(
    () => localStorage.getItem("cacherag-theme") !== "light",
  );

  const [webSearchEnabled, setWebSearchEnabled] = useState(
    () => localStorage.getItem("cacherag-web-search") === "true",
  );

  useEffect(() => {
    localStorage.setItem("cacherag-web-search", String(webSearchEnabled));
  }, [webSearchEnabled]);

  const [collections, setCollections] = useState([]);
  const [collectionId, setCollectionId] = useState("");
  const [documents, setDocuments] = useState([]);

  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [activeChat, setActiveChat] = useState(null);

  const [showCollectionModal, setShowCollectionModal] = useState(false);
  const [collectionName, setCollectionName] = useState("");
  const [collectionDescription, setCollectionDescription] = useState("");
  const [collectionSearch, setCollectionSearch] = useState("");

  const [metrics, setMetrics] = useState(null);
  const [requests, setRequests] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [cacheStats, setCacheStats] = useState(null);
  const [health, setHealth] = useState(null);

  const [copiedMessage, setCopiedMessage] = useState(null);

  const selectedCollection = collections.find(
    (item) => item.id === collectionId,
  );

  const notify = (message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 3000);
  };

  const loadCollections = useCallback(async (preferredId) => {
    try {
      const data = await api("/api/collections/");
      const list = Array.isArray(data) ? data : data.collections || [];

      setCollections(list);

      setCollectionId((current) => {
        const wanted = preferredId || current;

        if (wanted && list.some((item) => item.id === wanted)) {
          return wanted;
        }

        return list[0]?.id || "";
      });
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const loadDocuments = useCallback(async (id) => {
    if (!id) {
      setDocuments([]);
      return;
    }

    try {
      const data = await api(`/api/collections/${id}/documents`);
      setDocuments(Array.isArray(data) ? data : data.documents || []);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const loadHealth = useCallback(async () => {
    try {
      const response = await fetch("/health");
      const data = await response.json();
      setHealth(data);
    } catch {
      setHealth({ status: "unavailable", services: {} });
    }
  }, []);

  const loadDashboardData = useCallback(async () => {
    setPageLoading(true);

    const results = await Promise.allSettled([
      api("/api/metrics/summary"),
      api("/api/metrics/requests?limit=50"),
      api("/api/metrics/comparison"),
      api("/api/cache/stats"),
    ]);

    if (results[0].status === "fulfilled") {
      setMetrics(results[0].value);
    }

    if (results[1].status === "fulfilled") {
      setRequests(results[1].value.requests || []);
    }

    if (results[2].status === "fulfilled") {
      setComparison(results[2].value);
    }

    if (results[3].status === "fulfilled") {
      setCacheStats(results[3].value);
    }

    setPageLoading(false);
  }, []);

  useEffect(() => {
    loadCollections();
    loadHealth();
  }, [loadCollections, loadHealth]);

  useEffect(() => {
    loadDocuments(collectionId);
  }, [collectionId, loadDocuments]);

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("cacherag-theme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    if (page === "performance" || page === "settings") {
      loadDashboardData();
      loadHealth();
    }
  }, [page, loadDashboardData, loadHealth]);

  const startNewChat = () => {
    setMessages([]);
    setActiveChat(null);
    setQuestion("");
    setPage("chat");
    setMobileMenu(false);
  };

  const askQuestion = async (text = question) => {
    const cleanQuestion = text.trim();

    if (!cleanQuestion || !collectionId || loading) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: cleanQuestion,
    };

    const previousMessages = [...messages];

    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setLoading(true);
    setError("");

    try {
      const result = await api(`/api/collections/${collectionId}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: cleanQuestion,
          web_search_enabled: webSearchEnabled,
        }),
      });

      const assistantMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: result.answer || "No answer was returned.",
        sources: result.sources || [],
      };

      setMessages([...previousMessages, userMessage, assistantMessage]);

      setActiveChat((current) => current || crypto.randomUUID());
    } catch (err) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "error",
          content: err.message,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const createCollection = async (event) => {
    event.preventDefault();

    if (!collectionName.trim()) return;

    try {
      const created = await api("/api/collections/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: collectionName.trim(),
          description: collectionDescription.trim(),
        }),
      });

      setShowCollectionModal(false);
      setCollectionName("");
      setCollectionDescription("");

      await loadCollections(created.id);
      notify("Collection created");
    } catch (err) {
      setError(err.message);
    }
  };

  const renameCollection = async (collection) => {
    const newName = window.prompt(
      "Enter a new collection name:",
      collection.name,
    );

    if (!newName?.trim() || newName.trim() === collection.name) return;

    try {
      await api(`/api/collections/${collection.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim() }),
      });

      await loadCollections(collection.id);
      notify("Collection renamed");
    } catch (err) {
      setError(err.message);
    }
  };

  const deleteCollection = async (collection) => {
    if (!window.confirm(`Delete "${collection.name}" and all its documents?`)) {
      return;
    }

    try {
      await api(`/api/collections/${collection.id}`, {
        method: "DELETE",
      });

      setMessages([]);
      setActiveChat(null);
      await loadCollections();
      notify("Collection deleted");
    } catch (err) {
      setError(err.message);
    }
  };

  const uploadDocument = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";

    if (!file || !collectionId) return;

    const formData = new FormData();
    formData.append("file", file);

    setPageLoading(true);

    try {
      await api(`/api/collections/${collectionId}/documents`, {
        method: "POST",
        body: formData,
      });

      await loadDocuments(collectionId);
      await loadCollections(collectionId);
      notify("Document uploaded successfully");
    } catch (err) {
      setError(err.message);
    } finally {
      setPageLoading(false);
    }
  };

  const deleteDocument = async (document) => {
    if (!window.confirm(`Delete "${document.filename}"?`)) return;

    try {
      await api(`/api/documents/${document.id}`, {
        method: "DELETE",
      });

      await loadDocuments(collectionId);
      await loadCollections(collectionId);
      notify("Document deleted");
    } catch (err) {
      setError(err.message);
    }
  };

  const clearCache = async () => {
    if (!window.confirm("Clear all cached answers?")) return;

    try {
      const result = await api("/api/cache/answers", {
        method: "DELETE",
      });

      await loadDashboardData();

      notify(`Cache cleared · ${result?.deleted_entries ?? 0} entries removed`);
    } catch (err) {
      setError(err.message);
    }
  };

  const copyAnswer = async (message) => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedMessage(message.id);
      window.setTimeout(() => setCopiedMessage(null), 1600);
    } catch {
      setError("Could not copy this answer.");
    }
  };

  const filteredCollections = collections.filter((item) =>
    item.name.toLowerCase().includes(collectionSearch.toLowerCase()),
  );

  const chartData = [...requests]
    .slice(0, 12)
    .reverse()
    .map((item, index) => ({
      name: item.created_at
        ? new Date(item.created_at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })
        : `#${index + 1}`,
      response: Number(item.response_time_ms || 0),
    }));

  return (
    <div className="app-shell">
      {mobileMenu && (
        <button
          className="mobile-overlay"
          aria-label="Close navigation"
          onClick={() => setMobileMenu(false)}
        />
      )}

      <aside
        className={`sidebar ${sidebarOpen ? "" : "sidebar-collapsed"} ${
          mobileMenu ? "mobile-open" : ""
        }`}
      >
        <div className="brand">
          <div className="brand-mark">
            <Sparkles size={21} />
          </div>

          {sidebarOpen && (
            <div className="brand-copy">
              <strong>CacheRAG</strong>
              <span>Knowledge assistant</span>
            </div>
          )}

          {sidebarOpen && (
            <button
              className="icon-button sidebar-toggle"
              onClick={() => setSidebarOpen(false)}
              title="Collapse sidebar"
              aria-label="Collapse sidebar"
            >
              <ChevronRight size={17} />
            </button>
          )}
        </div>

        <button className="new-chat-button" onClick={startNewChat}>
          <Plus size={18} />
          {sidebarOpen && <span>New chat</span>}
        </button>

        <div className="nav-label">{sidebarOpen ? "WORKSPACE" : ""}</div>

        <nav className="main-nav">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`nav-item ${page === id ? "active" : ""}`}
              onClick={() => {
                setPage(id);
                setMobileMenu(false);
              }}
              title={label}
            >
              <Icon size={18} />
              {sidebarOpen && <span>{label}</span>}
              {sidebarOpen && page === id && <span className="active-dot" />}
            </button>
          ))}
        </nav>

        {sidebarOpen && (
          <div className="sidebar-collections">
            <div className="sidebar-section-heading">
              <span>YOUR COLLECTIONS</span>
              <button
                className="tiny-icon"
                onClick={() => setShowCollectionModal(true)}
                title="Add collection"
              >
                <Plus size={15} />
              </button>
            </div>

            {collections.slice(0, 6).map((item) => (
              <button
                key={item.id}
                className={`collection-shortcut ${
                  collectionId === item.id ? "selected" : ""
                }`}
                onClick={() => {
                  setCollectionId(item.id);
                  setPage("chat");
                  setMobileMenu(false);
                }}
              >
                <Database size={15} />
                <span>{item.name}</span>
              </button>
            ))}

            {collections.length === 0 && (
              <p className="sidebar-empty">
                Create a collection to get started.
              </p>
            )}
          </div>
        )}

        <div className="sidebar-bottom">
          <div className="connection-indicator">
            <span
              className={`status-dot ${
                health?.status === "healthy" ? "online" : "offline"
              }`}
            />

            {sidebarOpen && (
              <span>
                {health?.status === "healthy"
                  ? "All systems operational"
                  : "Checking services"}
              </span>
            )}
          </div>

          <button
            className="profile-button"
            onClick={() => setPage("settings")}
          >
            <div className="avatar">CR</div>

            {sidebarOpen && (
              <div className="profile-copy">
                <strong>CacheRAG</strong>
                <span>Local workspace</span>
              </div>
            )}

            {sidebarOpen && (
              <MoreHorizontal size={18} className="profile-more" />
            )}
          </button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button mobile-menu-button"
              onClick={() => setMobileMenu((value) => !value)}
            >
              <Menu size={20} />
            </button>

            {!sidebarOpen && (
              <button
                className="icon-button restore-sidebar-button"
                onClick={() => setSidebarOpen(true)}
                title="Show sidebar"
                aria-label="Show sidebar"
              >
                <Menu size={20} />
              </button>
            )}

            <div className="breadcrumbs">
              <span>Workspace</span>
              <ChevronRight size={14} />
              <strong>
                {navigation.find((item) => item.id === page)?.label}
              </strong>
            </div>
          </div>

          <div className="topbar-actions">
            {page === "chat" && (
              <div className="collection-select-wrap">
                <Database size={15} />

                <select
                  value={collectionId}
                  onChange={(event) => {
                    setCollectionId(event.target.value);
                    setMessages([]);
                    setActiveChat(null);
                  }}
                  aria-label="Choose collection"
                >
                  <option value="">Choose collection</option>
                  {collections.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>

                <ChevronDown size={14} />
              </div>
            )}

            <button
              className="icon-button theme-button"
              onClick={() => setDark((value) => !value)}
              title="Toggle theme"
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            <CircleHelp size={17} />
            <span>{error}</span>
            <button className="tiny-icon" onClick={() => setError("")}>
              <X size={16} />
            </button>
          </div>
        )}

        <div className="page-container">
          {page === "chat" && (
            <section className="chat-page">
              <div className="chat-main">
                {!messages.length ? (
                  <>
                    <div className="welcome-screen">
                      <div className="eyebrow">YOUR DOCUMENTS, UNDERSTOOD</div>

                      <h1>
                        Ask your knowledge base<span>.</span>
                      </h1>

                      <p>
                        Ask questions about your uploaded documents. CacheRAG
                        retrieves relevant passages and builds an answer
                        grounded in your sources.
                      </p>

                      {!collectionId && (
                        <div className="get-started-card">
                          <Database size={22} />

                          <div>
                            <strong>Choose a collection to begin</strong>
                            <span>
                              Create a collection and upload documents before
                              asking questions.
                            </span>
                          </div>

                          <button
                            className="primary-button"
                            onClick={() => setShowCollectionModal(true)}
                          >
                            Create collection
                          </button>
                        </div>
                      )}
                    </div>

                    {collectionId && (
                      <>
                        <div className="suggestion-grid">
                          {suggestions.map((suggestion) => (
                            <button
                              key={suggestion}
                              onClick={() => askQuestion(suggestion)}
                            >
                              <span>{suggestion}</span>
                              <ChevronRight size={16} />
                            </button>
                          ))}
                        </div>

                        <div className="welcome-collection">
                          <Database size={15} />
                          <span>
                            Using <strong>{selectedCollection?.name}</strong>
                          </span>
                          <span className="welcome-doc-count">
                            {documents.length} documents
                          </span>
                        </div>
                      </>
                    )}
                  </>
                ) : (
                  <div className="messages-list">
                    {messages.map((message) => (
                      <article
                        key={message.id}
                        className={`message-row ${message.role}`}
                      >
                        {message.role !== "user" && (
                          <div className={`message-avatar ${message.role}`}>
                            {message.role === "error" ? (
                              "!"
                            ) : (
                              <Sparkles size={17} />
                            )}
                          </div>
                        )}

                        <div className="message-content">
                          <div className="message-author">
                            {message.role === "user"
                              ? "You"
                              : message.role === "error"
                                ? "Request error"
                                : "CacheRAG"}
                          </div>

                          <div className="message-text">
                            {renderMessageText(message.content)}
                          </div>

                          {message.sources?.length > 0 && (
                            <div className="source-list">
                              <div className="source-heading">
                                <BookOpen size={14} />
                                Sources used
                              </div>

                              {message.sources.map((source, index) => (
                                <div
                                  className="source-item"
                                  key={`${source.source_type || "document"}-${
                                    source.document_id || source.url || index
                                  }-${index}`}
                                >
                                  {source.source_type === "web" ? (
                                    <>
                                      <Search size={14} />

                                      <a
                                        href={source.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                      >
                                        {source.title ||
                                          source.url ||
                                          `Web source ${index + 1}`}
                                      </a>

                                      <small>Web</small>
                                    </>
                                  ) : (
                                    <>
                                      <FileText size={14} />

                                      <span>
                                        {source.filename ||
                                          source.document_id ||
                                          `Source ${index + 1}`}
                                      </span>

                                      {source.page_number != null && (
                                        <small>Page {source.page_number}</small>
                                      )}
                                    </>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}

                          {message.role === "assistant" && (
                            <div className="message-tools">
                              <button onClick={() => copyAnswer(message)}>
                                {copiedMessage === message.id ? (
                                  <Check size={14} />
                                ) : (
                                  <Copy size={14} />
                                )}

                                {copiedMessage === message.id
                                  ? "Copied"
                                  : "Copy"}
                              </button>
                            </div>
                          )}
                        </div>

                        {message.role === "user" && (
                          <div className="message-avatar user">You</div>
                        )}
                      </article>
                    ))}

                    {loading && (
                      <div className="thinking-row">
                        <div className="message-avatar assistant">
                          <Sparkles size={17} />
                        </div>

                        <div className="thinking-bubble">
                          <LoaderCircle className="spin" size={17} />
                          Searching your knowledge base...
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className="composer-area">
                  <form
                    className="composer"
                    onSubmit={(event) => {
                      event.preventDefault();
                      askQuestion();
                    }}
                  >
                    <textarea
                      value={question}
                      onChange={(event) => setQuestion(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && !event.shiftKey) {
                          event.preventDefault();
                          askQuestion();
                        }
                      }}
                      placeholder={
                        collectionId
                          ? "Ask anything about your documents..."
                          : "Choose a collection first..."
                      }
                      disabled={!collectionId || loading}
                      rows={2}
                    />

                    <div className="composer-footer">
                      <button
                        className="send-button"
                        type="submit"
                        disabled={!question.trim() || !collectionId || loading}
                        aria-label="Send message"
                      >
                        {loading ? (
                          <LoaderCircle className="spin" size={17} />
                        ) : (
                          <Send size={17} />
                        )}
                      </button>
                    </div>
                  </form>

                  <p className="composer-disclaimer">
                    CacheRAG can make mistakes. Verify important information
                    against the original documents.
                  </p>
                </div>
              </div>
            </section>
          )}

          {page === "collections" && (
            <section className="content-page">
              <div className="page-heading">
                <div>
                  <div className="eyebrow">ORGANIZE YOUR KNOWLEDGE</div>
                  <h1>Collections</h1>
                  <p>Group documents by subject, project, or course.</p>
                </div>

                <button
                  className="primary-button"
                  onClick={() => setShowCollectionModal(true)}
                >
                  <Plus size={17} />
                  New collection
                </button>
              </div>

              <div className="toolbar">
                <div className="search-box">
                  <Search size={17} />
                  <input
                    value={collectionSearch}
                    onChange={(event) =>
                      setCollectionSearch(event.target.value)
                    }
                    placeholder="Search collections..."
                  />
                </div>

                <span className="result-count">
                  {filteredCollections.length} collections
                </span>
              </div>

              {filteredCollections.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">
                    <Database size={25} />
                  </div>
                  <h3>No collections found</h3>
                  <p>Create a collection to start organizing your documents.</p>

                  <button
                    className="primary-button"
                    onClick={() => setShowCollectionModal(true)}
                  >
                    <Plus size={16} />
                    Create collection
                  </button>
                </div>
              ) : (
                <div className="collection-grid">
                  {filteredCollections.map((collection) => (
                    <article className="collection-card" key={collection.id}>
                      <div className="collection-card-top">
                        <div className="collection-icon">
                          <Database size={20} />
                        </div>

                        <div className="card-actions">
                          <button
                            className="tiny-icon"
                            onClick={() => renameCollection(collection)}
                            title="Rename"
                          >
                            <MoreHorizontal size={18} />
                          </button>

                          <button
                            className="tiny-icon danger-hover"
                            onClick={() => deleteCollection(collection)}
                            title="Delete"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>

                      <h3>{collection.name}</h3>

                      <p>
                        {collection.description || "No description provided."}
                      </p>

                      <div className="collection-card-meta">
                        <span>
                          <FileText size={14} />
                          {collection.document_count ?? 0} documents
                        </span>

                        <span>Updated {formatDate(collection.updated_at)}</span>
                      </div>

                      <button
                        className="text-link"
                        onClick={() => {
                          setCollectionId(collection.id);
                          setPage("chat");
                        }}
                      >
                        Open collection
                        <ChevronRight size={15} />
                      </button>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}

          {page === "documents" && (
            <section className="content-page">
              <div className="page-heading">
                <div>
                  <div className="eyebrow">YOUR KNOWLEDGE LIBRARY</div>
                  <h1>Documents</h1>
                  <p>
                    Upload and manage the files used by your knowledge
                    assistant.
                  </p>
                </div>

                <label
                  className={`primary-button upload-button ${
                    !collectionId ? "disabled" : ""
                  }`}
                >
                  <Upload size={17} />
                  Upload document
                  <input
                    type="file"
                    accept=".pdf,.txt"
                    onChange={uploadDocument}
                    disabled={!collectionId || pageLoading}
                    hidden
                  />
                </label>
              </div>

              <div className="document-context">
                <div className="context-icon">
                  <Database size={17} />
                </div>

                <div>
                  <span>SELECTED COLLECTION</span>
                  <strong>
                    {selectedCollection?.name || "No collection selected"}
                  </strong>
                </div>

                <div className="context-count">{documents.length} files</div>

                <select
                  value={collectionId}
                  onChange={(event) => setCollectionId(event.target.value)}
                  aria-label="Select collection"
                >
                  <option value="">Choose collection</option>
                  {collections.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>

              {!collectionId ? (
                <div className="empty-state">
                  <Database size={28} />
                  <h3>Select a collection</h3>
                  <p>Choose a collection to see and manage its documents.</p>
                </div>
              ) : documents.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">
                    <FileText size={25} />
                  </div>
                  <h3>No documents yet</h3>
                  <p>
                    Upload a PDF or TXT file to give CacheRAG something to work
                    with.
                  </p>

                  <label className="primary-button upload-button">
                    <Upload size={16} />
                    Upload your first file
                    <input
                      type="file"
                      accept=".pdf,.txt"
                      onChange={uploadDocument}
                      hidden
                    />
                  </label>
                </div>
              ) : (
                <div className="document-table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>DOCUMENT</th>
                        <th>STATUS</th>
                        <th>PAGES</th>
                        <th>UPLOADED</th>
                        <th />
                      </tr>
                    </thead>

                    <tbody>
                      {documents.map((document) => (
                        <tr key={document.id}>
                          <td>
                            <div className="file-cell">
                              <div className="file-icon">
                                <FileText size={18} />
                              </div>

                              <div>
                                <strong>{document.filename}</strong>
                                <span>{document.id}</span>
                              </div>
                            </div>
                          </td>

                          <td>
                            <span
                              className={`status-pill ${String(
                                document.status || "processed",
                              ).toLowerCase()}`}
                            >
                              {document.status || "Processed"}
                            </span>
                          </td>

                          <td>
                            {document.page_count ?? document.pages ?? "—"}
                          </td>

                          <td>
                            {formatDate(
                              document.created_at || document.uploaded_at,
                            )}
                          </td>

                          <td className="table-actions">
                            <button
                              className="tiny-icon danger-hover"
                              onClick={() => deleteDocument(document)}
                              title="Delete document"
                            >
                              <Trash2 size={16} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="file-hint">
                <CircleHelp size={14} />
                Supported formats: PDF and TXT. Upload one file at a time.
              </div>
            </section>
          )}

          {page === "performance" && (
            <section className="content-page performance-page">
              <div className="page-heading">
                <div>
                  <div className="eyebrow">OBSERVE THE ENGINE</div>
                  <h1>Performance</h1>
                  <p>
                    Monitor request speed, cache effectiveness, and system
                    activity.
                  </p>
                </div>

                <button
                  className="secondary-button"
                  onClick={loadDashboardData}
                  disabled={pageLoading}
                >
                  <Activity size={16} />
                  {pageLoading ? "Refreshing..." : "Refresh metrics"}
                </button>
              </div>

              <div className="stats-grid">
                <StatCard
                  icon={Activity}
                  label="Total requests"
                  value={metrics?.total_requests ?? 0}
                  note="Recorded API requests"
                />

                <StatCard
                  icon={Zap}
                  label="Cache hit rate"
                  value={`${metrics?.cache_hit_rate_percent ?? 0}%`}
                  note={`${metrics?.cache_hits ?? 0} cache hits`}
                  accent
                />

                <StatCard
                  icon={Clock3}
                  label="Average response"
                  value={formatDuration(metrics?.average_response_time_ms)}
                  note="Across successful requests"
                />

                <StatCard
                  icon={Database}
                  label="Cached answers"
                  value={cacheStats?.cache?.cached_answers ?? 0}
                  note="Current answer cache"
                />
              </div>

              <div className="performance-grid">
                <div className="panel chart-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Response time</h3>
                      <p>Recent request duration</p>
                    </div>
                    <span className="panel-tag">Milliseconds</span>
                  </div>

                  <div className="chart-area">
                    {chartData.length ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData}>
                          <defs>
                            <linearGradient
                              id="responseFill"
                              x1="0"
                              y1="0"
                              x2="0"
                              y2="1"
                            >
                              <stop
                                offset="0%"
                                stopColor="#8874e8"
                                stopOpacity={0.28}
                              />
                              <stop
                                offset="95%"
                                stopColor="#8874e8"
                                stopOpacity={0}
                              />
                            </linearGradient>
                          </defs>

                          <CartesianGrid
                            strokeDasharray="3 3"
                            vertical={false}
                            stroke="var(--border)"
                          />

                          <XAxis
                            dataKey="name"
                            tickLine={false}
                            axisLine={false}
                            tick={{
                              fill: "var(--muted)",
                              fontSize: 11,
                            }}
                          />

                          <YAxis
                            tickLine={false}
                            axisLine={false}
                            tick={{
                              fill: "var(--muted)",
                              fontSize: 11,
                            }}
                          />

                          <Tooltip
                            contentStyle={{
                              background: "var(--panel)",
                              border: "1px solid var(--border)",
                              borderRadius: 10,
                              color: "var(--text)",
                            }}
                          />

                          <Area
                            type="monotone"
                            dataKey="response"
                            stroke="#8874e8"
                            strokeWidth={2}
                            fill="url(#responseFill)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="chart-empty">
                        <Activity size={23} />
                        <span>No request data yet</span>
                        <small>
                          Ask a question to start recording performance.
                        </small>
                      </div>
                    )}
                  </div>
                </div>

                <div className="panel breakdown-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Request breakdown</h3>
                      <p>Processing pipeline averages</p>
                    </div>
                  </div>

                  <MetricRow
                    label="Cache lookup"
                    value={metrics?.average_cache_lookup_time_ms}
                  />

                  <MetricRow
                    label="Retrieval"
                    value={metrics?.average_retrieval_time_ms}
                  />

                  <MetricRow
                    label="Reranking"
                    value={metrics?.average_rerank_time_ms}
                  />

                  <MetricRow
                    label="LLM generation"
                    value={metrics?.average_llm_time_ms}
                  />

                  <MetricRow
                    label="Cache write"
                    value={metrics?.average_cache_write_time_ms}
                  />
                </div>
              </div>

              <div className="panel comparison-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Cache impact</h3>
                    <p>Compare average cached and uncached response times.</p>
                  </div>

                  <div className="comparison-icon">
                    <Zap size={19} />
                  </div>
                </div>

                <div className="comparison-stats">
                  <div>
                    <span>Uncached average</span>
                    <strong>
                      {formatDuration(comparison?.uncached_average_ms)}
                    </strong>
                  </div>

                  <div>
                    <span>Cached average</span>
                    <strong className="positive">
                      {formatDuration(comparison?.cached_average_ms)}
                    </strong>
                  </div>

                  <div>
                    <span>Speedup factor</span>
                    <strong>
                      {comparison?.speedup_factor != null
                        ? `${Number(comparison.speedup_factor).toFixed(1)}×`
                        : "—"}
                    </strong>
                  </div>

                  <div>
                    <span>Time saved</span>
                    <strong className="positive">
                      {formatDuration(comparison?.time_saved_ms)}
                    </strong>
                  </div>
                </div>
              </div>

              <div className="panel request-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Recent requests</h3>
                    <p>Latest recorded question activity</p>
                  </div>

                  <span className="panel-tag">{requests.length} records</span>
                </div>

                {requests.length === 0 ? (
                  <div className="table-empty">
                    No requests have been recorded yet.
                  </div>
                ) : (
                  <div className="table-scroll">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>TIME</th>
                          <th>RESPONSE</th>
                          <th>CACHE</th>
                          <th>STATUS</th>
                        </tr>
                      </thead>

                      <tbody>
                        {requests.map((request, index) => (
                          <tr key={request.id || index}>
                            <td>
                              {request.created_at
                                ? new Date(request.created_at).toLocaleString()
                                : "—"}
                            </td>

                            <td>{formatDuration(request.response_time_ms)}</td>

                            <td>
                              <span
                                className={`status-pill ${
                                  ["hit", "semantic_hit"].includes(
                                    request.cache_status,
                                  )
                                    ? "success"
                                    : "neutral"
                                }`}
                              >
                                {request.cache_status === "semantic_hit"
                                  ? "Semantic Hit"
                                  : request.cache_status === "hit"
                                    ? "Hit"
                                    : "Miss"}
                              </span>
                            </td>

                            <td>
                              {request.success === false ? "Failed" : "Success"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </section>
          )}

          {page === "settings" && (
            <section className="content-page settings-page">
              <div className="page-heading">
                <div>
                  <div className="eyebrow">PREFERENCES & SYSTEM</div>
                  <h1>Settings</h1>
                  <p>Manage your workspace appearance and service tools.</p>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-section-title">
                  <h2>Appearance</h2>
                  <p>Customize how CacheRAG looks on this device.</p>
                </div>

                <div className="setting-row">
                  <div className="setting-icon">
                    {dark ? <Sun size={19} /> : <Moon size={19} />}
                  </div>

                  <div className="setting-copy">
                    <strong>Theme</strong>
                    <span>Choose a light or dark workspace.</span>
                  </div>

                  <button
                    className="theme-switch"
                    onClick={() => setDark((value) => !value)}
                  >
                    {dark ? <Moon size={15} /> : <Sun size={15} />}
                    {dark ? "Dark" : "Light"}
                  </button>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-section-title">
                  <h2>External web search</h2>
                  <p>
                    Allow CacheRAG to search the internet when your uploaded
                    documents don't contain enough information.
                  </p>
                </div>

                <div className="setting-row">
                  <div className="setting-icon">
                    <Search size={19} />
                  </div>

                  <div className="setting-copy">
                    <strong>Web search fallback</strong>
                    <span>
                      {webSearchEnabled
                        ? "Enabled — external sources may be used."
                        : "Disabled — answers use uploaded documents only."}
                    </span>
                  </div>

                  <button
                    className="theme-switch"
                    onClick={() => setWebSearchEnabled((value) => !value)}
                    aria-pressed={webSearchEnabled}
                  >
                    {webSearchEnabled ? "On" : "Off"}
                  </button>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-section-title">
                  <h2>System health</h2>
                  <p>Connection status for your backend services.</p>
                </div>

                <div className="health-list">
                  {["postgresql", "redis", "qdrant"].map((service) => {
                    const connected =
                      health?.services?.[service] === "connected";

                    return (
                      <div className="health-row" key={service}>
                        <div className="health-service-icon">
                          <Database size={17} />
                        </div>

                        <div className="setting-copy">
                          <strong>
                            {service === "postgresql"
                              ? "PostgreSQL"
                              : service[0].toUpperCase() + service.slice(1)}
                          </strong>

                          <span>
                            {connected
                              ? "Connected and responding"
                              : "Not connected or unavailable"}
                          </span>
                        </div>

                        <span
                          className={`health-badge ${
                            connected ? "healthy" : "unhealthy"
                          }`}
                        >
                          <span />
                          {connected ? "Connected" : "Disconnected"}
                        </span>
                      </div>
                    );
                  })}
                </div>

                <div className="health-footer">
                  <span>
                    API status: <strong>{health?.status || "Unknown"}</strong>
                  </span>

                  <button className="text-link" onClick={loadHealth}>
                    Check again
                    <Activity size={14} />
                  </button>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-section-title">
                  <h2>Cache management</h2>
                  <p>
                    Inspect Redis cache information and clear stored answers.
                  </p>
                </div>

                <div className="cache-info-grid">
                  <div>
                    <span>Cached answers</span>
                    <strong>{cacheStats?.cache?.cached_answers ?? "—"}</strong>
                  </div>

                  <div>
                    <span>Memory used</span>
                    <strong>
                      {cacheStats?.memory?.used_memory_human ?? "—"}
                    </strong>
                  </div>

                  <div>
                    <span>Memory limit</span>
                    <strong>
                      {cacheStats?.memory?.max_memory_human ?? "—"}
                    </strong>
                  </div>

                  <div>
                    <span>Eviction policy</span>
                    <strong>
                      {cacheStats?.memory?.eviction_policy ?? "—"}
                    </strong>
                  </div>
                </div>

                <div className="danger-zone">
                  <div>
                    <strong>Clear answer cache</strong>
                    <span>
                      Remove all CacheRAG answer-cache entries. New questions
                      will be generated again.
                    </span>
                  </div>

                  <button className="danger-button" onClick={clearCache}>
                    <Trash2 size={15} />
                    Clear cache
                  </button>
                </div>
              </div>

              <div className="about-footer">
                CacheRAG <span>·</span> Redis-powered RAG Knowledge Assistant
              </div>
            </section>
          )}
        </div>
      </main>

      {showCollectionModal && (
        <div
          className="modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setShowCollectionModal(false);
            }
          }}
        >
          <form className="modal-card" onSubmit={createCollection}>
            <div className="modal-heading">
              <div>
                <div className="eyebrow">NEW WORKSPACE</div>
                <h2>Create collection</h2>
              </div>

              <button
                type="button"
                className="icon-button"
                onClick={() => setShowCollectionModal(false)}
              >
                <X size={19} />
              </button>
            </div>

            <p className="modal-description">
              Create a place to organize documents around a topic or project.
            </p>

            <label className="field-label">Collection name</label>

            <input
              className="form-input"
              value={collectionName}
              onChange={(event) => setCollectionName(event.target.value)}
              placeholder="e.g. Machine Learning Notes"
              required
              autoFocus
            />

            <label className="field-label">
              Description <span>Optional</span>
            </label>

            <textarea
              className="form-input form-textarea"
              value={collectionDescription}
              onChange={(event) => setCollectionDescription(event.target.value)}
              placeholder="What will this collection contain?"
              rows={3}
            />

            <div className="modal-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setShowCollectionModal(false)}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="primary-button"
                disabled={!collectionName.trim()}
              >
                <Plus size={16} />
                Create collection
              </button>
            </div>
          </form>
        </div>
      )}

      {toast && (
        <div className="toast-message">
          <Check size={16} />
          {toast}
        </div>
      )}
    </div>
  );
}

function StatCard({ icon: Icon, label, value, note, accent }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${accent ? "accent" : ""}`}>
        <Icon size={19} />
      </div>

      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      <span className="stat-note">{note}</span>
    </div>
  );
}

function MetricRow({ label, value }) {
  const number = Number(value || 0);
  const width = Math.min(100, Math.max(2, number / 20));

  return (
    <div className="metric-row">
      <div className="metric-label">
        <span>{label}</span>
        <strong>{formatDuration(value)}</strong>
      </div>

      <div className="metric-track">
        <div style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

export default App;
