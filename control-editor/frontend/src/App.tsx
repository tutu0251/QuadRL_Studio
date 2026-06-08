import { useCallback, useEffect, useState } from "react";
import { api, wsLogsUrl } from "./api/client";
import { useEditorStore } from "./stores/editorStore";
import { MenuBar } from "./features/menu/MenuBar";
import { Toolbar } from "./features/toolbar/Toolbar";
import { ModelSummaryBar } from "./features/summary/ModelSummaryBar";
import { JointsWorkbench } from "./features/workbench/JointsWorkbench";
import { SettingsRail } from "./features/inspector/SettingsRail";
import { ConsoleDock } from "./features/console/ConsoleDock";
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
    { name: string; hasPhyUrdf: boolean; hasControl: boolean }[]
  >([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [railWidth, resizeRail] = useClampedSize(340, 260, 560);

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
        log("Connected to Control Editor API");
      })
      .catch(() => {
        setConnected(false);
        setError("Backend unreachable — start control-editor on port 8002");
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
      if (r.hasControl) await reloadModel(name);
      else log(`Loaded ${name} — File → Import phy URDF`);
      await refreshProjects();
    } catch (e) {
      setError(String(e));
    }
  };

  const importPhy = async () => {
    if (!project) return;
    setError(null);
    try {
      const r = await api.importPhy(project);
      setModel(r.model);
      log(`Imported phy_${project}.urdf → ProfileA auto-generated`);
      await refreshProjects();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="app control-app">
      <header className="top-bar">
        <div className="menu-row">
          <MenuBar
            projects={projects}
            projectDetails={projectDetails}
            onLoadProject={loadProject}
            onImport={importPhy}
            onReload={() => project && reloadModel(project)}
          />
        </div>
        <div className="action-row">
          <Toolbar />
          <ConsoleDock />
        </div>
      </header>

      {error && (
        <div className="error-bar" role="alert">
          {error}
          <button type="button" className="error-dismiss" onClick={() => setError(null)} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      <div className="editor-body">
        <ModelSummaryBar />
        <div className="workbench-row">
          <main className="workbench-main">
            <JointsWorkbench />
          </main>
          <ResizeHandle axis="horizontal" onResize={(d) => resizeRail(-d)} />
          <aside className="settings-rail" style={{ width: railWidth }}>
            <SettingsRail />
          </aside>
        </div>
      </div>

      <StatusBar connected={connected} />
    </div>
  );
}
