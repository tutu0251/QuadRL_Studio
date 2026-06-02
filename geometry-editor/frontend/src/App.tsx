import { useCallback, useEffect, useState } from "react";
import { api, wsLogsUrl } from "./api/client";
import { useEditorStore } from "./stores/editorStore";
import { MenuBar } from "./features/menu/MenuBar";
import { Toolbar } from "./features/toolbar/Toolbar";
import { Viewport3D } from "./features/viewport/Viewport3D";
import { HierarchyPanel } from "./features/hierarchy/HierarchyPanel";
import { InspectorPanel } from "./features/inspector/InspectorPanel";
import { PoseEditorPanel } from "./features/pose/PoseEditorPanel";
import { ConsolePanel } from "./features/console/ConsolePanel";
import { MeasurePanel } from "./features/measure/MeasurePanel";
import { ResizeHandle } from "./components/ResizeHandle";
import { useClampedSize } from "./hooks/useClampedSize";

export default function App() {
  const project = useEditorStore((s) => s.project);
  const setProject = useEditorStore((s) => s.setProject);
  const setModel = useEditorStore((s) => s.setModel);
  const log = useEditorStore((s) => s.log);
  const [projects, setProjects] = useState<string[]>([]);
  const [newProjectName, setNewProjectName] = useState("my_robot");
  const [error, setError] = useState<string | null>(null);
  const [consoleOpen, setConsoleOpen] = useState(true);
  const editorMode = useEditorStore((s) => s.editorMode);
  const setEditorMode = useEditorStore((s) => s.setEditorMode);
  const [leftWidth, resizeLeft] = useClampedSize(260, 160, 480);
  const [rightWidth, resizeRight] = useClampedSize(320, 200, 560);
  const [toolsHeight, resizeTools] = useClampedSize(140, 64, 320);
  const [consoleHeight, resizeConsole] = useClampedSize(120, 80, 400);

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
    if (r.active) setProject(r.active);
  }, [setProject]);

  useEffect(() => {
    refreshProjects().catch(() => {});
    api.health().then(() => log("Connected to backend v2")).catch(() => setError("Backend unreachable"));
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

  const withProject = async (fn: () => Promise<void>) => {
    if (!project) {
      setError("Select or create a project first");
      return;
    }
    setError(null);
    try {
      await fn();
      await reloadModel(project);
    } catch (e) {
      setError(String(e));
    }
  };

  const createProject = async () => {
    setError(null);
    try {
      const r = await api.createProject(newProjectName);
      setProject(r.project);
      setModel(r.model);
      await refreshProjects();
      log(`Created project ${r.project}`);
    } catch (e) {
      setError(String(e));
    }
  };

  const loadProject = async (name: string) => {
    setError(null);
    try {
      const r = await api.loadProject(name);
      setProject(r.project);
      setModel(r.model);
      log(`Loaded ${name}`);
    } catch (e) {
      setError(String(e));
    }
  };

  const addChildLink = (parentId: string) =>
    withProject(async () => {
      await api.addChildLink(project!, parentId, {
        name: "new_link",
        joint_name: "new_joint",
        joint_type: "revolute",
      });
      log("Added child link");
    });

  const deleteLink = (linkId: string) =>
    withProject(async () => {
      await api.removeLink(project!, linkId);
      log("Removed link subtree");
    });

  return (
    <div className="app unity-layout">
      <div className="top-bar">
        <MenuBar
          projects={projects}
          newProjectName={newProjectName}
          setNewProjectName={setNewProjectName}
          onCreateProject={createProject}
          onLoadProject={loadProject}
          onReloadModel={reloadModel}
        />
        <Toolbar />
      </div>

      {error && <div className="error-bar">{error}</div>}

      <div className="editor-body">
        <div className="editor-main">
          <aside className="left-dock" style={{ width: leftWidth }}>
            {editorMode === "model" ? (
              <HierarchyPanel onAddChild={addChildLink} onDeleteLink={deleteLink} />
            ) : (
              <PoseEditorPanel />
            )}
          </aside>

          <ResizeHandle axis="horizontal" onResize={resizeLeft} />

          <main className="center-dock">
            <div className="viewport-area">
              <Viewport3D />
            </div>
            <ResizeHandle axis="vertical" onResize={(d) => resizeTools(-d)} />
            <div className="bottom-tools" style={{ height: toolsHeight }}>
              <MeasurePanel />
            </div>
          </main>

          <ResizeHandle axis="horizontal" onResize={(d) => resizeRight(-d)} />

          <aside className="right-dock" style={{ width: rightWidth }}>
            {editorMode === "model" ? (
              <InspectorPanel />
            ) : (
              <div className="pose-side-hint">
                Use sliders to tune the stand pose. Export geometry to update training spawn.
              </div>
            )}
          </aside>
        </div>

        {consoleOpen && (
          <ResizeHandle axis="vertical" onResize={(d) => resizeConsole(-d)} />
        )}

        <div className={`bottom-dock ${consoleOpen ? "open" : "collapsed"}`}>
          <button
            type="button"
            className="console-toggle"
            onClick={() => setConsoleOpen(!consoleOpen)}
          >
            Console {consoleOpen ? "▼" : "▲"}
          </button>
          {consoleOpen && (
            <div className="console-content" style={{ height: consoleHeight }}>
              <ConsolePanel />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
