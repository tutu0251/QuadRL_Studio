import { useCallback, useEffect, useState } from "react";
import { api, wsLogsUrl } from "./api/client";
import { useEditorStore } from "./stores/editorStore";
import { MenuBar } from "./features/menu/MenuBar";
import { Toolbar } from "./features/toolbar/Toolbar";
import { HierarchyPanel } from "./features/hierarchy/HierarchyPanel";
import { InspectorPanel } from "./features/inspector/InspectorPanel";
import { SummaryPanel } from "./features/summary/SummaryPanel";
import { ConsolePanel } from "./features/console/ConsolePanel";
import { StatusBar } from "./features/status/StatusBar";
import { ResizeHandle } from "./components/ResizeHandle";
import { useClampedSize } from "./hooks/useClampedSize";

export default function App() {
  const project = useEditorStore((s) => s.project);
  const setProject = useEditorStore((s) => s.setProject);
  const setModel = useEditorStore((s) => s.setModel);
  const log = useEditorStore((s) => s.log);
  const [projects, setProjects] = useState<string[]>([]);
  const [projectDetails, setProjectDetails] = useState<
    { name: string; hasCtrlUrdf: boolean; hasSensor: boolean }[]
  >([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consoleOpen, setConsoleOpen] = useState(true);
  const [leftWidth, resizeLeft] = useClampedSize(280, 200, 480);
  const [rightWidth, resizeRight] = useClampedSize(360, 280, 640);
  const [consoleHeight, resizeConsole] = useClampedSize(130, 80, 400);

  const reloadModel = useCallback(
    async (name: string) => {
      const m = await api.getModel(name);
      setModel(m);
    },
    [setModel]
  );

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
        log("Connected to Sensor Editor API");
      })
      .catch(() => {
        setConnected(false);
        setError("Backend unreachable — start sensor-editor on port 8003");
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
    try {
      const r = await api.loadProject(name);
      setProject(r.project);
      setModel(r.model);
      if (r.hasSensor) await reloadModel(name);
      else log(`Loaded ${name} — File → Import ctrl URDF`);
      await refreshProjects();
    } catch (e) {
      setError(String(e));
    }
  };

  const importCtrl = async () => {
    if (!project) return;
    setError(null);
    try {
      const r = await api.importCtrl(project);
      setModel(r.model);
      log(`Imported ctrl_${project}_ros2_control.urdf`);
      await refreshProjects();
    } catch (e) {
      setError(String(e));
    }
  };

  const bootstrapQuadruped = async () => {
    if (!project) return;
    setError(null);
    try {
      const m = await api.bootstrapQuadruped(project);
      setModel(m);
      log("Bootstrap: base IMU + foot contacts");
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="app unity-layout control-app sensor-app">
      <div className="top-bar">
        <MenuBar
          projects={projects}
          projectDetails={projectDetails}
          onLoadProject={loadProject}
          onImport={importCtrl}
          onBootstrap={bootstrapQuadruped}
          onReload={() => project && reloadModel(project)}
        />
        <Toolbar />
      </div>

      {error && (
        <div className="error-bar" role="alert">
          {error}
          <button type="button" className="error-dismiss" onClick={() => setError(null)} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      <div className="editor-body">
        <div className="editor-main">
          <aside className="left-dock" style={{ width: leftWidth }}>
            <HierarchyPanel />
          </aside>
          <ResizeHandle axis="horizontal" onResize={resizeLeft} />
          <main className="center-dock">
            <SummaryPanel />
          </main>
          <ResizeHandle axis="horizontal" onResize={(d) => resizeRight(-d)} />
          <aside className="right-dock" style={{ width: rightWidth }}>
            <InspectorPanel />
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
