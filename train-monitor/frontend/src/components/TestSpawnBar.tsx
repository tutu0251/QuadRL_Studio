import { useEffect, useState } from "react";
import { ActionButton } from "./ActionButton";
import { api } from "../api/client";
import { useCommandPreview } from "../hooks/useCommandPreview";

type Props = {
  project: string | null;
  busy: boolean;
  gazeboHeadless: boolean;
  guiAvailable: boolean;
  resolvedDisplay: string | null;
  onBusy: (v: boolean) => void;
  onError: (msg: string | null) => void;
  onGazeboHeadlessChange: (v: boolean) => void;
};

export function TestSpawnBar({
  project,
  busy,
  gazeboHeadless,
  guiAvailable,
  resolvedDisplay,
  onBusy,
  onError,
  onGazeboHeadlessChange,
}: Props) {
  const [running, setRunning] = useState(false);
  const preview = useCommandPreview(project, "test_spawn", {
    headless: gazeboHeadless,
  });
  const stopPreview = useCommandPreview(project, "test_spawn_stop");

  useEffect(() => {
    if (!project) {
      setRunning(false);
      return;
    }
    void api
      .getSpawnTestStatus(project)
      .then((status) => {
        setRunning(status.state === "running" || status.state === "starting");
      })
      .catch(() => setRunning(false));
  }, [project]);

  const runTestSpawn = async () => {
    if (!project || running) return;
    onBusy(true);
    onError(null);
    try {
      const result = await api.testSpawn(project, { headless: gazeboHeadless });
      const active = result.state === "running" && result.valid;
      setRunning(active);
      if (!result.valid && result.errors?.length) {
        onError(result.errors.join("; "));
      }
    } catch (e) {
      onError(String(e));
      setRunning(false);
    } finally {
      onBusy(false);
    }
  };

  const stopTestSpawn = async () => {
    if (!project || !running) return;
    onBusy(true);
    onError(null);
    try {
      await api.stopSpawnTest(project);
      setRunning(false);
    } catch (e) {
      onError(String(e));
    } finally {
      onBusy(false);
    }
  };

  const sessionBusy = busy || running;

  return (
    <div className="test-spawn-bar">
      <div className="test-spawn-actions">
        <div className="gazebo-mode" role="radiogroup" aria-label="Gazebo mode">
          <span className="gazebo-mode-label">Gazebo</span>
          <label className="radio-pill">
            <input
              type="radio"
              name="test-spawn-gazebo-mode"
              checked={gazeboHeadless}
              disabled={sessionBusy}
              onChange={() => onGazeboHeadlessChange(true)}
            />
            Headless
          </label>
          <label className="radio-pill" title={guiAvailable ? undefined : "No X11 display on training host"}>
            <input
              type="radio"
              name="test-spawn-gazebo-mode"
              checked={!gazeboHeadless}
              disabled={sessionBusy || !guiAvailable}
              onChange={() => onGazeboHeadlessChange(false)}
            />
            GUI
          </label>
        </div>
        <ActionButton
          className="btn primary"
          disabled={!project || sessionBusy}
          command={preview.preview?.command}
          commandLoading={preview.loading}
          onClick={() => void runTestSpawn()}
        >
          Test spawn
        </ActionButton>
        {running && (
          <ActionButton
            className="btn danger"
            disabled={!project || busy}
            command={stopPreview.preview?.command}
            commandLoading={stopPreview.loading}
            onClick={() => void stopTestSpawn()}
          >
            Stop test spawn
          </ActionButton>
        )}
      </div>
      <p className="panel-hint test-spawn-hint">
        {running
          ? "Spawn test session is running — Gazebo stays up until you stop it."
          : "Uses built workspace sim.launch.py (world flat), effective spawn pose, and exported joint angles."}
        {!guiAvailable && " No display — use Headless or set QUADRL_DISPLAY."}
        {guiAvailable && !gazeboHeadless && resolvedDisplay && ` GUI uses DISPLAY=${resolvedDisplay}.`}
      </p>
    </div>
  );
}
