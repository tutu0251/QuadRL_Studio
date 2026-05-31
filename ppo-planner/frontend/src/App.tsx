import { useCallback, useEffect, useState } from "react";
import { api, wsLogsUrl } from "./api/client";
import { usePlannerStore } from "./stores/plannerStore";
import { MenuBar } from "./features/menu/MenuBar";
import { Toolbar } from "./features/toolbar/Toolbar";
import { MachinePanel } from "./features/machine/MachinePanel";
import { InspectorTabs } from "./features/tabs/InspectorTabs";
import { OverviewPanel } from "./features/overview/OverviewPanel";
import { ConsolePanel } from "./features/console/ConsolePanel";
import { StatusBar } from "./features/status/StatusBar";
import { ResizeHandle } from "./components/ResizeHandle";
import { useClampedSize } from "./hooks/useClampedSize";

export default function App() {
  const project = usePlannerStore((s) => s.project);
  const setProject = usePlannerStore((s) => s.setProject);
  const setModel = usePlannerStore((s) => s.setModel);
  const setValidation = usePlannerStore((s) => s.setValidation);
  const log = usePlannerStore((s) => s.log);
  const [projects, setProjects] = useState<string[]>([]);
  const [projectDetails, setProjectDetails] = useState<
    { name: string; hasSensor: boolean; hasPpo: boolean }[]
  >([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consoleOpen, setConsoleOpen] = useState(true);
  const [leftWidth, resizeLeft] = useClampedSize(320, 260, 420);
  const [rightWidth, resizeRight] = useClampedSize(400, 320, 560);
  const [consoleHeight, resizeConsole] = useClampedSize(140, 88, 360);

  const refreshProjects = useCallback(async () => {
    const r = await api.listProjects();
    setProjects(r.projects);
    setProjectDetails(r.details ?? []);
    if (r.active) setProject(r.active);
  }, [setProject]);

  useEffect(() => {
    refreshProjects().catch(() => {});
    api
      .health()
      .then(() => {
        setConnected(true);
        log("Connected to PPO Planner API");
      })
      .catch(() => {
        setConnected(false);
        setError("Backend unreachable — start ppo-planner on port 8004");
      });
  }, [refreshProjects, log]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsLogsUrl());
      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data);
        if (data.entry) log(`[${data.entry.level}] ${data.entry.message}`);
      };
    } catch {
      /* ignore */
    }
    return () => ws?.close();
  }, [log]);

  const loadProject = async (name: string) => {
    setError(null);
    setValidation(null);
    try {
      const r = await api.loadProject(name);
      setProject(r.project);
      setModel(r.model);
      log(`Loaded ${name}`);
      const v = await api.validate(name);
      setValidation(v);
      await refreshProjects();
    } catch (e) {
      setError(String(e));
    }
  };

  const bootstrap = async () => {
    if (!project) return;
    setError(null);
    try {
      const r = await api.bootstrap(project);
      setModel(r.model);
      log("Bootstrapped PPO config with machine recommendations");
      const v = await api.validate(project);
      setValidation(v);
      await refreshProjects();
    } catch (e) {
      setError(String(e));
    }
  };

  const resetBaseline = async () => {
    if (!project) return;
    try {
      const m = await api.resetBaseline(project);
      setModel(m);
      setValidation(null);
      log("Reset to stable-baselines3 baseline defaults");
    } catch (e) {
      log(String(e));
    }
  };

  return (
    <div className="app unity-layout ppo-app">
      <div className="top-bar">
        <MenuBar
          projects={projects}
          projectDetails={projectDetails}
          onLoadProject={loadProject}
          onBootstrap={bootstrap}
          onResetBaseline={resetBaseline}
        />
        <Toolbar />
      </div>

      {error && (
        <div className="error-bar" role="alert">
          {error}
          <button
            type="button"
            className="error-dismiss"
            onClick={() => setError(null)}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      <div className="editor-body">
        <div className="editor-main">
          <aside className="left-dock" style={{ width: leftWidth }}>
            <MachinePanel />
          </aside>
          <ResizeHandle axis="horizontal" onResize={resizeLeft} />
          <main className="center-dock">
            <OverviewPanel />
          </main>
          <ResizeHandle axis="horizontal" onResize={(d) => resizeRight(-d)} />
          <aside className="right-dock" style={{ width: rightWidth }}>
            <InspectorTabs />
          </aside>
        </div>

        {consoleOpen && <ResizeHandle axis="vertical" onResize={(d) => resizeConsole(-d)} />}

        <div className={`bottom-dock ${consoleOpen ? "open" : "collapsed"}`}>
          <button
            type="button"
            className="console-toggle"
            onClick={() => setConsoleOpen(!consoleOpen)}
          >
            <span>Console</span>
            <span className="console-toggle-meta">{consoleOpen ? "▼" : "▲"}</span>
          </button>
          {consoleOpen && (
            <div className="console-content" style={{ height: consoleHeight }}>
              <ConsolePanel />
            </div>
          )}
        </div>
      </div>

      <StatusBar connected={connected} />
    </div>
  );
}
