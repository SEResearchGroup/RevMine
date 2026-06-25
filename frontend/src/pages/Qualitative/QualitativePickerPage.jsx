import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  MessageSquareText, RefreshCw, Loader2, AlertCircle, CheckCircle2,
  Plus, Search, X, Database, Hammer, FolderGit2, ChevronRight,
} from "lucide-react";
import {
  qualitativeService, collectionService, workspaceService, getApiErrorMessage,
} from "../../services/api";

const norm = (data, keys) => {
  if (Array.isArray(data)) return data;
  for (const k of keys) if (Array.isArray(data?.[k])) return data[k];
  return [];
};

const PlatformBadge = ({ platform }) => (
  <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
    {platform || "?"}
  </span>
);

function ProgressBar({ pct }) {
  return (
    <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
      <div className="h-full bg-purple-500 transition-all" style={{ width: `${Math.min(100, pct || 0)}%` }} />
    </div>
  );
}

/* One horizontal card. `card.status` is one of:
   collecting | finalizing | paused | collection_failed (collection-backed)
   pending | building | ready | failed (dataset-backed) */
function QualCard({ card, busy, onOpen, onPrepare }) {
  const repo = card.repo || "(unknown repo)";
  const stats = card.dataset?.stats || {};

  const left = (
    <div className="flex items-center gap-3 min-w-0">
      <div className="w-10 h-10 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center shrink-0">
        <MessageSquareText className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium text-gray-800 truncate">{repo}</p>
          <PlatformBadge platform={card.platform} />
        </div>
        <p className="text-xs text-gray-400">Collection #{card.collection_id}</p>
      </div>
    </div>
  );

  // READY ------------------------------------------------------------------
  if (card.status === "ready") {
    return (
      <div onClick={() => onOpen(card.dataset.id)}
        className="flex items-center justify-between gap-4 bg-white border border-gray-200/70 rounded-xl px-4 py-3 hover:shadow-md hover:border-purple-200 cursor-pointer transition-all">
        {left}
        <div className="flex items-center gap-6 shrink-0">
          <Metric n={stats.reviews_count} label="reviews" />
          <Metric n={stats.comments_human} label="comments" />
          <span className="inline-flex items-center gap-1.5 text-xs text-green-700 bg-green-50 px-2 py-1 rounded-full">
            <CheckCircle2 className="w-3.5 h-3.5" /> Ready
          </span>
          <ChevronRight className="w-4 h-4 text-gray-300" />
        </div>
      </div>
    );
  }

  // PENDING (collected, not prepared) -> click to prepare --------------------
  if (card.status === "pending") {
    return (
      <div onClick={() => !busy && onPrepare(card.dataset.id)}
        className="flex items-center justify-between gap-4 bg-white border border-gray-200/70 rounded-xl px-4 py-3 hover:border-purple-300 cursor-pointer transition-all">
        {left}
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-gray-500">Collected · not prepared</span>
          <button disabled={busy}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-white bg-purple-600 hover:bg-purple-700 px-3 py-1.5 rounded-lg disabled:opacity-60">
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Hammer className="w-3.5 h-3.5" />}
            {busy ? "Preparing…" : "Prepare data"}
          </button>
        </div>
      </div>
    );
  }

  // BUILDING / FINALIZING ---------------------------------------------------
  if (card.status === "building" || card.status === "finalizing") {
    const label = card.status === "building" ? "Preparing data from JSON…" : "Finalizing collection…";
    return (
      <div className="flex items-center justify-between gap-4 bg-white border border-gray-200/70 rounded-xl px-4 py-3">
        {left}
        <span className="inline-flex items-center gap-2 text-xs text-blue-700 shrink-0">
          <Loader2 className="w-4 h-4 animate-spin" /> {label}
        </span>
      </div>
    );
  }

  // COLLECTING --------------------------------------------------------------
  if (card.status === "collecting" || card.status === "paused") {
    const p = card.plan || {};
    const pct = p.progress_percentage || 0;
    return (
      <div className="bg-white border border-gray-200/70 rounded-xl px-4 py-3">
        <div className="flex items-center justify-between gap-4 mb-2">
          {left}
          <span className="inline-flex items-center gap-2 text-xs shrink-0 text-gray-500">
            {card.status === "paused"
              ? <>Paused</>
              : <><Loader2 className="w-3.5 h-3.5 animate-spin text-purple-600" /> Collecting… {p.collected_items ?? 0}/{p.total_items ?? "?"}{p.is_total_approximate ? "~" : ""}</>}
          </span>
        </div>
        <ProgressBar pct={pct} />
      </div>
    );
  }

  // FAILED ------------------------------------------------------------------
  const isDataset = card.kind === "dataset";
  return (
    <div className="flex items-center justify-between gap-4 bg-white border border-red-200 rounded-xl px-4 py-3">
      {left}
      <div className="flex items-center gap-3 shrink-0">
        <span className="inline-flex items-center gap-1.5 text-xs text-red-700">
          <AlertCircle className="w-3.5 h-3.5" /> {isDataset ? "Preparation failed" : "Collection failed"}
        </span>
        {isDataset && (
          <button disabled={busy} onClick={() => onPrepare(card.dataset.id)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 border border-gray-300 hover:border-purple-400 px-3 py-1.5 rounded-lg">
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        )}
      </div>
    </div>
  );
}

const Metric = ({ n, label }) => (
  <div className="text-center">
    <p className="text-sm font-semibold text-gray-800">{n ?? "—"}</p>
    <p className="text-[10px] text-gray-400">{label}</p>
  </div>
);

function CollectModal({ onClose, onStarted }) {
  const [workspaces, setWorkspaces] = useState([]);
  const [repos, setRepos] = useState([]);
  const [wsId, setWsId] = useState("");
  const [repoSearch, setRepoSearch] = useState("");
  const [repoId, setRepoId] = useState("");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [ws, rp] = await Promise.all([
          workspaceService.getAll(),
          workspaceService.getAllRepositories(),
        ]);
        setWorkspaces(norm(ws.data, ["results", "workspaces"]));
        setRepos(norm(rp.data, ["repositories", "results"]));
      } catch (e) {
        setError(getApiErrorMessage(e, "Failed to load workspaces/repositories"));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const wsRepos = useMemo(() => {
    let list = repos;
    if (wsId) list = list.filter((r) => String(r.workspace ?? r.workspace_id) === String(wsId));
    if (repoSearch.trim()) {
      const q = repoSearch.toLowerCase();
      list = list.filter((r) => (r.full_name || r.name || "").toLowerCase().includes(q));
    }
    return list;
  }, [repos, wsId, repoSearch]);

  const selectedRepo = useMemo(() => repos.find((r) => String(r.id) === String(repoId)), [repos, repoId]);

  const start = async () => {
    if (!selectedRepo) return;
    setStarting(true);
    setError(null);
    try {
      const wid = selectedRepo.workspace ?? selectedRepo.workspace_id ?? wsId;
      const startRes = await collectionService.startCollection(wid, selectedRepo.id);
      const planId = startRes.data.collection_plan.id;
      const platform = (selectedRepo.platform || selectedRepo.workspace_platform || "").toLowerCase();
      const metrics = platform.includes("gitlab") ? ["mr_title"] : ["pr_title"];
      await collectionService.configureMetrics(planId, {
        selected_metrics: metrics,
        status: ["open", "closed", "merged"],
        for_qualitative: true,
      });
      await collectionService.executeCollection(planId);
      onStarted();
      onClose();
    } catch (e) {
      setError(getApiErrorMessage(e, "Failed to start collection"));
      setStarting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-lg p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">Collect qualitative data</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
        </div>

        {error && <div className="mb-3 p-2.5 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="flex items-center gap-2 text-gray-500 py-8 justify-center"><Loader2 className="w-4 h-4 animate-spin" /> Loading…</div>
        ) : (
          <>
            <label className="block text-sm font-medium text-gray-700 mb-1">Workspace</label>
            <select value={wsId} onChange={(e) => { setWsId(e.target.value); setRepoId(""); }}
              className="w-full mb-4 px-3 py-2 border border-gray-300 rounded-lg text-sm">
              <option value="">All workspaces</option>
              {workspaces.map((w) => <option key={w.id} value={w.id}>{w.name || `Workspace ${w.id}`}</option>)}
            </select>

            <label className="block text-sm font-medium text-gray-700 mb-1">Repository</label>
            <div className="relative mb-2">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input value={repoSearch} onChange={(e) => setRepoSearch(e.target.value)} placeholder="Search repositories…"
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500" />
            </div>
            <div className="max-h-56 overflow-y-auto border border-gray-100 rounded-lg divide-y">
              {wsRepos.length === 0 ? (
                <p className="text-sm text-gray-400 p-4 text-center">No repositories found.</p>
              ) : wsRepos.map((r) => (
                <label key={r.id} className={`flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-50 ${String(repoId) === String(r.id) ? "bg-purple-50" : ""}`}>
                  <input type="radio" name="repo" checked={String(repoId) === String(r.id)} onChange={() => setRepoId(String(r.id))} />
                  <FolderGit2 className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-700 truncate">{r.full_name || r.name}</span>
                  <PlatformBadge platform={r.platform || r.workspace_platform} />
                </label>
              ))}
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
              <button onClick={start} disabled={!repoId || starting}
                className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50">
                {starting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
                Start collection
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function QualitativePickerPage() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [showCollect, setShowCollect] = useState(false);
  const [toast, setToast] = useState(null);
  const prevStatus = useRef({});

  const load = useCallback(async () => {
    try {
      setError(null);
      const [ds, pl] = await Promise.all([
        qualitativeService.getDatasets(),
        collectionService.getAllPlans().then((r) => r.data).catch(() => []),
      ]);
      setDatasets(ds.datasets || []);
      setPlans(Array.isArray(pl) ? pl : (pl?.results || []));
    } catch (e) {
      setError(getApiErrorMessage(e, "Failed to load qualitative datasets"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [load]);

  const cards = useMemo(() => {
    const byColl = new Map();
    for (const d of datasets) {
      byColl.set(d.collection_id, {
        key: `ds-${d.id}`, kind: "dataset", collection_id: d.collection_id,
        status: d.status, repo: d.repository_full_name, platform: d.platform, dataset: d,
      });
    }
    for (const p of plans) {
      if (!p.for_qualitative || byColl.has(p.id)) continue;
      let status = "collecting";
      if (p.status === "completed") status = "finalizing";
      else if (p.status === "failed") status = "collection_failed";
      else if (p.status === "paused") status = "paused";
      byColl.set(p.id, {
        key: `pl-${p.id}`, kind: "collection", collection_id: p.id,
        status, repo: p.repository_full_name, platform: p.platform, plan: p,
      });
    }
    return Array.from(byColl.values());
  }, [datasets, plans]);

  // toast on transitions (collection finished / dataset ready)
  useEffect(() => {
    for (const c of cards) {
      const prev = prevStatus.current[c.collection_id];
      if (prev && prev !== c.status) {
        if (c.status === "pending" && (prev === "collecting" || prev === "finalizing")) {
          setToast(`Collection finished for ${c.repo} — ready to prepare.`);
        } else if (c.status === "ready" && prev === "building") {
          setToast(`${c.repo} is ready to explore.`);
        }
      }
      prevStatus.current[c.collection_id] = c.status;
    }
  }, [cards]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(t);
  }, [toast]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return cards;
    return cards.filter((c) =>
      `${c.repo} ${c.platform} ${c.status}`.toLowerCase().includes(q));
  }, [cards, search]);

  const ready = filtered.filter((c) => c.status === "ready");
  const notReady = filtered.filter((c) => c.status !== "ready");

  const handlePrepare = async (datasetId) => {
    setBusyId(datasetId);
    try {
      await qualitativeService.rebuildDataset(datasetId);
      await load();
    } catch (e) {
      setError(getApiErrorMessage(e, "Failed to prepare dataset"));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-gray-900 text-white text-sm px-4 py-2.5 rounded-lg shadow-lg flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-green-400" /> {toast}
        </div>
      )}

      <div className="flex items-center justify-between gap-4 mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">Qualitative Analysis</h1>
        <button onClick={() => setShowCollect(true)}
          className="inline-flex items-center gap-2 bg-purple-600 text-white px-4 py-2.5 rounded-lg font-medium hover:bg-purple-700">
          <Plus className="w-4 h-4" /> Collect qualitative data
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by repository, platform or status…"
          className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500" />
      </div>

      {error && <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}

      {loading ? (
        <div className="flex items-center gap-2 text-gray-500"><Loader2 className="w-4 h-4 animate-spin" /> Loading…</div>
      ) : cards.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <MessageSquareText className="w-10 h-10 mx-auto mb-3 text-gray-300" />
          <p>No qualitative data yet.</p>
          <p className="text-sm">Use “Collect qualitative data” to start.</p>
        </div>
      ) : (
        <div className="space-y-8">
          <Section title="In preparation" subtitle="Collecting, or collected and awaiting preparation" cards={notReady}
            empty="Nothing in progress." render={(c) => (
              <QualCard key={c.key} card={c} busy={busyId === c.dataset?.id} onOpen={(id) => navigate(`/qualitative/${id}`)} onPrepare={handlePrepare} />
            )} />
          <Section title="Ready to explore" subtitle="Prepared datasets you can open" cards={ready}
            empty="No ready datasets yet." render={(c) => (
              <QualCard key={c.key} card={c} onOpen={(id) => navigate(`/qualitative/${id}`)} onPrepare={handlePrepare} />
            )} />
        </div>
      )}

      {showCollect && <CollectModal onClose={() => setShowCollect(false)} onStarted={load} />}
    </div>
  );
}

function Section({ title, subtitle, cards, empty, render }) {
  return (
    <div>
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-gray-700">{title} <span className="text-gray-400 font-normal">· {cards.length}</span></h2>
        <p className="text-xs text-gray-400">{subtitle}</p>
      </div>
      {cards.length === 0 ? (
        <p className="text-sm text-gray-400 py-3">{empty}</p>
      ) : (
        <div className="space-y-2.5 max-h-[55vh] overflow-y-auto pr-1">
          {cards.map(render)}
        </div>
      )}
    </div>
  );
}
