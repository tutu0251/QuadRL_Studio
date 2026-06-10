"""Training-Predictor API — Optuna + Claude parameter tuning.

FastAPI service mirroring the other QuadRL editor backends (open CORS, ``main:app`` entry).
A study is launched in a background thread; the frontend polls status / streams logs.
"""
from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.models import LogsResponse, StartTuningRequest, StartTuningResponse  # noqa: E402
from api.task_manager import task_manager  # noqa: E402
from tuner import config_io, paths, study as study_mod  # noqa: E402

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="QuadRL Training Predictor API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    from tuner import advisor as advisor_mod
    from tuner import monitor_client
    adv = advisor_mod.make_advisor()
    mon = monitor_client.TrainMonitorClient()
    return {
        "status": "ok",
        "editor": "training-predictor",
        "projects_root": str(paths.projects_root()),
        "advisor_key": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "advisor_backend": adv.backend if adv.available else "disabled",
        "advisor_detail": adv.describe(),
        "monitor_url": mon.base,
        "monitor_reachable": mon.reachable(),
    }


@app.get("/api/projects")
def list_projects():
    return {"projects": paths.list_projects()}


@app.get("/api/projects/{project}/stages")
def project_stages(project: str):
    """Curriculum stages for a project (id + human name + order), so the UI can let the
    user choose stages by name. Returns enabled=False / empty for non-curriculum projects."""
    if project not in paths.list_projects():
        raise HTTPException(404, f"Unknown project '{project}'")
    rl, _ = config_io.load_base(project)
    cur = rl.get("curriculum") or {}
    stages = sorted((cur.get("stages") or []), key=lambda s: s.get("order", 0))
    return {
        "enabled": bool(cur.get("enabled")),
        "stages": [
            {
                "id": s.get("id"),
                "name": s.get("name") or s.get("id") or f"Stage {i + 1}",
                "order": s.get("order", i),
                "timesteps": s.get("timesteps"),
            }
            for i, s in enumerate(stages)
        ],
    }


@app.get("/api/projects/{project}/studies")
def list_studies(project: str):
    """Past tuning studies for a project (each its own Optuna sqlite DB under tuning/),
    so the UI can offer to resume one. Newest first."""
    import optuna

    if project not in paths.list_projects():
        raise HTTPException(404, f"Unknown project '{project}'")
    root = paths.tuning_root(project)
    out: list[dict] = []
    if root.exists():
        for d in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            db = d / "optuna.db"
            if not db.is_file():
                continue
            try:
                summaries = optuna.get_all_study_summaries(f"sqlite:///{db}")
            except Exception:
                continue
            for s in summaries:
                best = getattr(s, "best_trial", None)
                out.append({
                    "study_name": s.study_name,
                    "n_trials": s.n_trials,
                    "best_value": (round(float(best.value), 5)
                                   if best is not None and best.value is not None else None),
                    "datetime_start": (s.datetime_start.isoformat()
                                       if getattr(s, "datetime_start", None) else None),
                })
    return {"studies": out}


@app.get("/api/projects/{project}/sequences")
def list_sequences(project: str):
    """Past per-stage sequences for a project (each with a ``sequence.json``), so the UI can
    resume one. Newest first."""
    import json as _jsonlib

    if project not in paths.list_projects():
        raise HTTPException(404, f"Unknown project '{project}'")
    root = paths.tuning_root(project)
    out: list[dict] = []
    if root.exists():
        for d in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            f = d / "sequence.json"
            if not f.is_file():
                continue
            try:
                data = _jsonlib.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            results = data.get("stage_results") or {}
            done = sum(1 for r in results.values() if r.get("status") == "done")
            out.append({
                "seq_name": data.get("seq_name") or d.name,
                "stages_tuned": len(results),
                "stages_done": done,
                "stages_to_tune": data.get("stages_to_tune") or [],
            })
    return {"sequences": out}


def _session_or_404(task_id: str) -> study_mod.StudySession:
    session = study_mod.get(task_id)
    if session is None:
        raise HTTPException(404, f"No tuning session {task_id}")
    return session


@app.post("/api/tuning/start", response_model=StartTuningResponse)
def start_tuning(req: StartTuningRequest):
    if req.project not in paths.list_projects():
        raise HTTPException(404, f"Unknown project '{req.project}'")
    task_id = task_manager.create_task()

    if req.mode == "sequential_stage":
        from tuner import stage_sequence

        rl, _ = config_io.load_base(req.project)
        cur = rl.get("curriculum") or {}
        stages = sorted((cur.get("stages") or []), key=lambda s: s.get("order", 0))
        if not (cur.get("enabled") and stages):
            raise HTTPException(400, "Sequential per-stage tuning needs a curriculum with stages.")
        if req.stages_to_tune:
            stages_to_tune = [k for k in req.stages_to_tune if 0 <= k < len(stages)]
        elif req.max_stages:
            stages_to_tune = list(range(min(req.max_stages, len(stages))))
        else:
            stages_to_tune = list(range(len(stages)))
        if not stages_to_tune:
            raise HTTPException(400, "No valid stages selected to tune.")
        seq_cfg = stage_sequence.StageSeqConfig(
            project=req.project,
            stages_to_tune=stages_to_tune,
            trials_per_stage=req.trials_per_stage,
            timesteps_per_stage=req.timesteps_per_stage,
            advisor_every_n=req.advisor_every_n,
            gazebo_headless=req.gazebo_headless,
            trial_timeout=req.trial_timeout,
            mock_objective=req.mock_objective,
            monitor_base_url=req.monitor_base_url,
            seq_name=req.study_name or ("seq_" + time.strftime("%Y%m%d_%H%M%S")),
        )
        session = stage_sequence.StageSequenceSession(config=seq_cfg, log=task_manager.bind(task_id))
        study_mod.register(task_id, session)
        threading.Thread(target=session.run, name=f"seq-{task_id[:8]}", daemon=True).start()
        return StartTuningResponse(task_id=task_id, study_name=seq_cfg.seq_name)

    cfg = study_mod.StudyConfig(
        project=req.project,
        n_trials=req.n_trials,
        advisor_every_n=req.advisor_every_n,
        trial_timesteps=req.trial_timesteps,
        gazebo_headless=req.gazebo_headless,
        max_stages=req.max_stages,
        monitor_base_url=req.monitor_base_url,
        mock_objective=req.mock_objective,
        include_hyperparams=req.include_hyperparams,
        include_reward_weights=req.include_reward_weights,
        include_reward_params=req.include_reward_params,
        study_name=req.study_name or ("study_" + time.strftime("%Y%m%d_%H%M%S")),
        trial_timeout=req.trial_timeout,
    )
    session = study_mod.StudySession(config=cfg, log=task_manager.bind(task_id))
    study_mod.register(task_id, session)
    threading.Thread(target=session.run, name=f"tuning-{task_id[:8]}", daemon=True).start()
    return StartTuningResponse(task_id=task_id, study_name=cfg.study_name)


@app.get("/api/tuning/{task_id}/status")
def status(task_id: str):
    return _session_or_404(task_id).to_status()


@app.get("/api/tuning/{task_id}/logs", response_model=LogsResponse)
def logs(task_id: str, since: int = 0):
    if not task_manager.exists(task_id):
        raise HTTPException(404, f"No tuning session {task_id}")
    entries, nxt = task_manager.logs_since(task_id, since)
    return LogsResponse(entries=entries, next=nxt)


@app.get("/api/tuning/{task_id}/trials")
def trials(task_id: str):
    import optuna

    session = _session_or_404(task_id)
    if session._study is None:
        return {"trials": []}
    rows = []
    for t in session._study.trials:
        rows.append({
            "number": t.number,
            "value": (round(float(t.value), 5) if t.value is not None else None),
            "state": t.state.name if hasattr(t.state, "name") else str(t.state),
            "params": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in t.params.items()},
        })
    return {"trials": rows}


@app.post("/api/tuning/{task_id}/stop")
def stop(task_id: str):
    session = _session_or_404(task_id)
    session.request_stop()
    return {"ok": True, "status": session.status}


@app.post("/api/tuning/{task_id}/apply")
def apply_best(task_id: str):
    """Save the study's best (confirmed) params back into the selected project's configs.

    Global mode writes the one shared param set; sequential mode writes each tuned stage's
    winning reward terms into ``curriculum.stages[i].reward_terms``.
    """
    from tuner import config_writer, stage_sequence

    session = _session_or_404(task_id)
    try:
        if isinstance(session, stage_sequence.StageSequenceSession):
            stage_params = session.best_stage_params()
            if not stage_params:
                raise HTTPException(400, "No tuned stages to apply yet.")
            summary = config_writer.apply_stage_params(session.config.project, stage_params)
            return {"ok": True, "mode": "sequential_stage", **summary}
        if not session.best or not session.best.get("params"):
            raise HTTPException(400, "No best trial to apply yet.")
        summary = config_writer.apply_params(session.config.project, session.best["params"])
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"ok": True, "applied_from_trial": session.best.get("number"), **summary}


@app.get("/api/tuning/{task_id}/stream")
async def stream(task_id: str):
    if not task_manager.exists(task_id):
        raise HTTPException(404, f"No tuning session {task_id}")

    async def gen():
        cursor = 0
        while True:
            entries, cursor = task_manager.logs_since(task_id, cursor)
            for e in entries:
                yield f"event: log\ndata: {_json(e)}\n\n"
            session = study_mod.get(task_id)
            if session is not None:
                yield f"event: status\ndata: {_json(session.to_status())}\n\n"
                if session.status in ("complete", "stopped", "error"):
                    # flush any final logs then end
                    entries, cursor = task_manager.logs_since(task_id, cursor)
                    for e in entries:
                        yield f"event: log\ndata: {_json(e)}\n\n"
                    yield "event: done\ndata: {}\n\n"
                    return
            await asyncio.sleep(1.0)

    return StreamingResponse(gen(), media_type="text/event-stream")


def _json(obj) -> str:
    import json
    return json.dumps(obj)


# ---- static page ----
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    page = STATIC_DIR / "index.html"
    if page.exists():
        return FileResponse(str(page))
    return {"service": "training-predictor", "hint": "static page not found"}
