# Phase 1 Build Spec — Sequential Per-Stage Tuning

**Status:** ✅ IMPLEMENTED (backend + API + frontend). Verified via the mock loop
(`tests/test_stage_sequence_mock.py`) and a live mock run through the API. Real-training
validation (one micro-run) is the remaining check before production use.

Modules delivered: `tuner/config_io.materialize_stage`, `tuner/config_writer.apply_stage_params`,
`tuner/checkpoints.py`, `tuner/stage_sequence.py`; API `mode=sequential_stage` dispatch +
`/api/projects/{p}/sequences`; frontend mode toggle, `StageProgressPanel`, per-stage apply.

---

_Original proposal below (kept for reference)._
**Depends on:** Phase 0 (done) — the Train Monitor's `/train/resume` accepts `resume_checkpoint`
+ `resume_start_stage` + a custom `config_path`, all forwarded to `run_rl_train.py`
(`--resume / --start-stage / --config`). Confirmed live via dry-run.

---

## 1. Goal & scope

Tune **each curriculum stage independently** so each stage gets its own reward/penalty
profile (Stand firmly, Recover rapidly, Walk softly, …), trained greedily: lock stage *k*,
freeze its checkpoint, then tune stage *k+1* warm-started from it.

**In scope (Phase 1):**
- A new `StageSequenceSession` running one Optuna **sub-study per stage**.
- Per-stage reward-term search space (`rw.* / rp.*` built from *that stage's* terms).
- Trial → Train Monitor resume mapping (single-stage warm start).
- Checkpoint capture & hand-off between stages.
- Per-stage write-back into `curriculum.stages[i].reward_terms`.
- Sequence resume (continue from the first un-tuned stage).
- API + minimal UI (mode switch + per-stage progress).

**Out of scope (Phase 1):**
- Tuning PPO **hyperparameters** per stage — they stay curriculum-wide. Phase 1 leaves them
  at the project's PPO config (a later optional "global hyperparameter pre-pass" can set them
  once). See [Open decision #1](#11-open-decisions-to-confirm).
- Concurrent trials (the Train Monitor is a single controller — trials are serial on **Axis B**;
  each trial still uses `num_envs` env-parallelism on **Axis A**).

---

## 2. New / changed modules

| File | Change |
|---|---|
| `backend/tuner/stage_sequence.py` | **new** — `StageSequenceSession`, `StageSeqConfig`, the loop |
| `backend/tuner/config_io.py` | **add** `materialize_stage(...)` (truncate to 0..k, write stage k's reward_terms) |
| `backend/tuner/config_writer.py` | **add** `apply_stage_params(project, {k: params})` (write per-stage reward_terms) |
| `backend/tuner/search_space.py` | reuse `SearchSpace.from_base(stage_terms, include_hyperparams=False)` — no change expected |
| `backend/tuner/checkpoints.py` | **new** — `locate_stage_checkpoint(run_root, project, stage)` + capture/copy helpers |
| `backend/api/models.py` | **add** `mode`, `trials_per_stage`, `timesteps_per_stage` to the request; sequence status models |
| `backend/api/main.py` | dispatch `mode` → `StageSequenceSession`; sequence status/stream endpoints |
| `frontend/...` | mode toggle, per-stage progress panel, per-stage Apply (Phase 1 UI) |

`StudySession` (today's global study) is **untouched** — sequential mode is additive.

---

## 3. Data model

```text
StageSeqConfig:
  project: str
  stages_to_tune: list[int]        # 0-based indices, e.g. [0,1,2] from "Train Up To Stage"
  trials_per_stage: int            # M (default 10)
  timesteps_per_stage: int         # per-trial proxy budget for the single stage
  advisor_every_n: int             # Claude review cadence within each stage's sub-study
  gazebo_headless: bool
  trial_timeout: float | None
  seq_name: str                    # "seq_<timestamp>" (or reused for resume)

StageResult (one per stage):
  stage_index: int
  stage_id: str
  stage_name: str
  status: "pending" | "running" | "done" | "failed"
  n_completed: int
  best_value: float | None
  best_params: dict[str, float]    # rw.* / rp.* for THIS stage
  seed_checkpoint: str | None      # frozen ckpt this stage produced (seed for next)
  decisions: list[dict]            # advisor decisions during this stage
```

Persisted to `tuning/<seq_name>/sequence.json` after each stage locks (for resume).

Layout on disk:
```
<project>/tuning/<seq_name>/
  sequence.json
  stage_0/ optuna.db  trial_<n>/config.yaml  best_ckpt.zip
  stage_1/ optuna.db  trial_<n>/config.yaml  best_ckpt.zip
  ...
```

---

## 4. The `StageSequenceSession` loop (pseudocode)

```python
def run(self):
    rl, ppo = config_io.load_base(project)
    stages = sorted(curriculum.stages, key=order)        # full list (0-based)
    seq_dir = tuning_root(project) / cfg.seq_name
    state = load_sequence_json(seq_dir)                  # resume: restore results + seed + start_k
    seed = state.last_seed_checkpoint                    # None on a fresh sequence

    for k in cfg.stages_to_tune[state.start_k:]:
        stage = stages[k]
        result = StageResult(k, stage.id, stage.name, status="running")
        space = SearchSpace.from_base(stage["reward_terms"],
                                      include_hyperparams=False,    # rewards only
                                      include_reward_weights=True,
                                      include_reward_params=True)
        study = optuna.create_study(storage=f"sqlite:///{seq_dir}/stage_{k}/optuna.db",
                                    direction="maximize", load_if_exists=True,
                                    sampler=TPESampler())
        advisor = make_advisor(log=self.log)

        def objective(trial):
            sampled = space.sample(trial)                # rw.<id> / rp.<id>.sigma for THIS stage
            cfg_dict = config_io.materialize_stage(rl, ppo, sampled,
                                                   stage_index=k,
                                                   budget=cfg.timesteps_per_stage)
            cfg_path = write_trial_config(cfg_dict, seq_dir/f"stage_{k}/trial_{trial.number}/config.yaml")
            t0 = time.time()
            status = self._train_stage(k, cfg_path, seed)        # ← monitor start/resume (see §6)
            run_root = trial_runner.resolve_run_dir(project, status["run_id"], after=t0)
            value, _ = trial_runner.read_objective(run_root)     # stage k's final eval/mean_reward
            ckpt = checkpoints.capture_stage_ckpt(run_root, project, stage,
                                                  dest=seq_dir/f"stage_{k}/trial_{trial.number}_ckpt.zip")
            trial.set_user_attr("ckpt", str(ckpt))               # remember which file is this trial's
            return value

        remaining = cfg.trials_per_stage - count_completed(study)
        study.optimize(objective, n_trials=max(0, remaining),
                       callbacks=[advisor_callback(advisor, space, study, result)])

        best = study.best_trial
        seed = checkpoints.promote_best(best.user_attrs["ckpt"],
                                        dest=seq_dir/f"stage_{k}/best_ckpt.zip")   # frozen seed for k+1
        result.update(status="done", best_value=best.value,
                      best_params=best.params, seed_checkpoint=seed)
        self.stage_results[k] = result
        save_sequence_json(seq_dir, self.stage_results, last_seed=seed)
        checkpoints.cleanup_trial_ckpts(seq_dir/f"stage_{k}", keep=best.number)   # disk economy

    self.status = "complete"
```

**Advisor:** reuses the existing `make_advisor` / `apply_decision`, scoped to the stage's
sub-study (Claude reviews this stage's trials every `advisor_every_n`). Decisions stored in
`result.decisions` and `stage_<k>/decisions.jsonl`.

---

## 5. Per-stage search space

`SearchSpace.from_base(stage["reward_terms"], include_hyperparams=False, …)` already produces
`rw.<id>` (0…2× current magnitude) and `rp.<id>.sigma` (0.4×…2.5×) from whatever terms the
**stage** defines. Because each stage carries its own 26 terms with its own base weights, each
stage's search space is naturally stage-specific. No change to `search_space.py` expected.

---

## 6. Trial → Train Monitor mapping (the core mechanic)

Each trial trains **only stage k**, warm-started from the previous stage's frozen checkpoint,
using a per-trial config whose curriculum is **truncated to stages 0..k**.

```python
def _train_stage(self, k, cfg_path, seed):
    if k == 0 or seed is None:
        # First stage: no checkpoint to seed from. Config's curriculum = [stage 0] only,
        # so the trainer's auto stage-detection trains stage 0 from scratch.
        return monitor.run_to_completion(
            project, cfg_path, gazebo_headless=cfg.gazebo_headless,
            timeout=cfg.trial_timeout, should_stop=lambda: self.stop_requested)
    else:
        # Later stage: resume from stage k-1's frozen checkpoint and train ONLY stage k.
        # Truncated config (0..k) + start-stage k ⇒ stages 0..k-1 are skipped (carry-forward),
        # stage k (the last in the config) is the only one trained, seeded from `seed`.
        return monitor.run_to_completion(
            project, cfg_path,
            resume_checkpoint=seed,            # → POST /train/resume, --resume
            resume_start_stage=k,              # → --start-stage k  (0-based)
            gazebo_headless=cfg.gazebo_headless,
            timeout=cfg.trial_timeout, should_stop=lambda: self.stop_requested)
```

| Stage | Endpoint | `--config` | `--resume` | `--start-stage` | Trains |
|---|---|---|---|---|---|
| k = 0 | `/train/start` | trial cfg (curriculum=[stage 0]) | — | — | stage 0 from scratch |
| k ≥ 1 | `/train/resume` | trial cfg (curriculum=stages 0..k) | `best_ckpt` of k−1 | `k` | only stage k, seeded |

`materialize_stage(rl, ppo, sampled, stage_index=k, budget)`:
1. `deepcopy(rl)`, drop `ppo_config_file`, inline PPO `hyperparameters` (unchanged from base).
2. Truncate `curriculum.stages` to indices `0..k` (k+1 stages).
3. Apply `sampled` `rw.*/rp.*` into **`stages[k].reward_terms`** (sign preserved per term, exactly
   like today's global write but targeted at the stage's own block).
4. Set `stages[k].timesteps = budget`. Earlier stages' timesteps are irrelevant (skipped).

> Trainer behaviour relied on (verified Phase 0): `--start-stage k` with `--resume` seeds stage k
> from the checkpoint with a **fresh timestep budget** and trains it to the end of the (truncated)
> config — which is stage k itself. ([run_rl_train.py](../../training/scripts/run_rl_train.py) §`_resolve_start_stage_override`, stage loop ~L996.)

---

## 7. Checkpoint capture & hand-off

The trainer writes each stage's final checkpoint into the **project-level** checkpoint dir, named
by stage. Successive trials of the same stage **overwrite** it, so we capture each trial's
checkpoint *before the next trial runs* (safe because trials are serial — single monitor controller).

**Phase 0.5 — CONFIRMED** (read of [run_rl_train.py](../../training/scripts/run_rl_train.py) + on-disk check):
- **Location:** `<project>/checkpoints/` (`config.checkpoint.directory`, default `checkpoints`;
  resolved by `_checkpoint_dir`, falls back to `<project>/checkpoints`). *Project-level, not per-run.*
- **Filename:** `<basename>.zip` where `basename = filename_template` (default `ppo_{stage_id}`) →
  e.g. `ppo_stand.zip`, `ppo_walk.zip` (periodic saves are `ppo_walk_275000_steps.zip`; we want the
  final `ppo_<stage_id>.zip`). Verified on disk for `my_robot`.
- **Seeding is from OUR checkpoint:** with `--start-stage k` + `--resume <our seed>`, the trainer
  trains stage k with `resume = our seed` (run_rl_train.py L1021-1023), **not** any leftover file in
  the shared dir. Since stage k is the last stage in the truncated config, the loop ends after it —
  no carry-forward to later stages. ✅

Helpers:
- `locate_stage_ckpt(project, stage, config)` → `<project>/checkpoints/<basename>.zip` (compute
  `basename` with the same template logic; honor config overrides).
- `capture_stage_ckpt(project, stage, config, dest)` — after a trial completes, copy that file to a
  trial-specific path and return it (no re-run of the winner).
- `promote_best(captured_ckpt, dest)` — copy the winning trial's checkpoint to
  `stage_<k>/best_ckpt.zip` → the frozen **seed** for stage k+1 (read-only thereafter; passed as an
  absolute `--resume` path, which the trainer's resolver accepts).
- `cleanup_trial_ckpts(...)` — delete non-winning trial copies to bound disk.

> **Fallback** (documented, not needed given the above): if per-trial capture ever proved
> unreliable, re-run the winning params once and copy the produced checkpoint (+1 training/stage).

---

## 8. Per-stage write-back (Apply)

Final, user-confirmed step (mirrors today's `apply_best`), but per stage:

`config_writer.apply_stage_params(project, results)`:
- For each tuned stage k, write its `best_params` (`rw.*/rp.*`) into
  `rl_<project>_config.yaml` → `curriculum.stages[k].reward_terms` (matching by term id, sign
  preserved). This is the block the trainer actually reads per stage (`stage_config()`), so the
  tuned weights take effect.
- Back up the RL config first (`.bak-<timestamp>`), like the existing writer.
- Hyperparameters: unchanged in Phase 1.

Returns a summary (per-stage term counts, file, backup) for the UI.

---

## 9. Objective (per stage)

`trial_runner.read_objective(run_root)` returns the **last** `eval/mean_reward` (fallback
`rollout/ep_rew_mean`). Since the trial trained only stage k, that last value **is** stage k's
final score. No change needed. Higher = better, as today.

---

## 10. API surface

**Request** (extend `StartTuningRequest`, or a sibling `StartSequenceRequest`):
```jsonc
{
  "project": "my_robot",
  "mode": "sequential_stage",        // vs "global" (today's behaviour, default)
  "stages_to_tune": [0,1,2],         // derived from "Train Up To Stage" = 1..K
  "trials_per_stage": 10,
  "timesteps_per_stage": 30000,
  "advisor_every_n": 5,
  "gazebo_headless": true,
  "trial_timeout": null,
  "seq_name": null                   // set to resume an existing sequence
}
```

**Endpoints:**
- `POST /api/tuning/start` — when `mode == "sequential_stage"`, build a `StageSequenceSession`.
- `GET /api/tuning/{task_id}/status` — extended status (below).
- `GET /api/tuning/{task_id}/stream` — unchanged SSE (logs + status).
- `GET /api/projects/{project}/sequences` — list resumable sequences (like `/studies`).
- `POST /api/tuning/{task_id}/apply` — calls `apply_stage_params` in sequential mode.

**Status shape (sequential):**
```jsonc
{
  "mode": "sequential_stage",
  "status": "running",
  "seq_name": "seq_20260610_1500",
  "current_stage_index": 1,
  "total_stages": 3,
  "stages": [ /* StageResult per stage: name, status, n_completed, best_value, best_params */ ],
  "decisions": [ /* current stage's advisor decisions */ ]
}
```

---

## 11. Sequence resume

Reuses the persistence in `sequence.json`:
- On start with a `seq_name`, load `stage_results` + `last_seed_checkpoint`, set `start_k` to the
  first stage whose status ≠ `done`, and continue.
- Each completed stage's Optuna DB (`stage_<k>/optuna.db`) also reloads via `load_if_exists`, so a
  stage interrupted mid-way resumes its own trials too (same logic as the global-study resume we
  already shipped).

---

## 12. UI (Phase 1, minimal)

- **Mode toggle** in Study Setup: *Single global study* ↔ *Sequential per-stage*.
- When sequential: show `trials_per_stage` + `timesteps_per_stage` (reuse friendly labels); the
  existing **Train Up To Stage** picker defines which stages are tuned (1..K).
- **Per-stage progress panel:** a row per stage — name · status (pending/running/done) ·
  trials done · best score — with the active stage highlighted. *Best so far* shows the current
  stage's best; *Claude's insights* shows the current stage's decisions.
- **Apply** writes all stages' tuned reward_terms (confirm dialog, lists per-stage changes).

---

## 13. Edge cases & errors

| Case | Handling |
|---|---|
| A stage has no `reward_terms` | Skip tuning; train once to produce the seed, mark `done` (best_params empty). |
| All trials in a stage fail | Abort the sequence with a clear error (no seed to hand off). |
| User stops mid-sequence | `should_stop` halts the monitor; `sequence.json` already persisted → resumable. |
| Best trial's checkpoint missing | Fallback: re-run winning params once, then promote (see §7). |
| `trial_timeout` exceeded | Monitor stops that trial; Optuna records it failed; continue. |
| Resume target total < already done | Stage's `remaining ≤ 0` → skip to next stage. |

---

## 14. Test plan

- **Unit:** `materialize_stage` truncates curriculum to 0..k and writes only `stages[k].reward_terms`;
  per-stage search space is built from the stage's own terms; `apply_stage_params` writes the right
  blocks + backup.
- **Mock loop:** a `mock_objective`-style path for sequences (synthetic per-stage scores, no
  training) to exercise the full `StageSequenceSession` loop, checkpoint hand-off (stubbed), resume,
  and status — fast, no GPU/monitor.
- **Dry-run integration:** assert the monitor receives the correct `--config` / `--resume` /
  `--start-stage` per stage (extend the Phase 0 dry-run check across k=0 and k≥1).
- **One real micro-run** (2 stages, tiny budget) to validate checkpoint location + seeding end-to-end.

---

## 15. Effort & sequencing

1. `materialize_stage` + `apply_stage_params` + per-stage search-space wiring (+ unit tests).
2. `checkpoints.py` (+ the mini Phase-0.5 checkpoint-location check).
3. `StageSequenceSession` loop + `sequence.json` persistence + mock path.
4. API (request/status/list/apply) + dispatch.
5. Frontend (mode toggle, per-stage progress, Apply).
6. Dry-run + micro-run verification; docs update.

Backend (1–4) is the bulk and is independently testable via the mock path before any UI.

---

## 16. Decisions — LOCKED ✅

Confirmed by the user; these are the Phase 1 choices.

1. **Hyperparameters** — **fixed** at the project's PPO config for Phase 1 (no per-stage hp; a
   global hyperparameter pre-pass can be added later, out of scope here).
2. **Checkpoint capture** — **per-trial copy** (capture each trial's stage checkpoint right after
   it finishes; no extra training). Re-run-the-winner is the documented fallback (§7) only if
   per-trial capture proves unreliable.
3. **Budgets** — **uniform** `trials_per_stage` / `timesteps_per_stage` across stages (optional
   per-stage overrides deferred).
4. **Stage selection** — **reuse "Train Up To Stage"**: tune stages 1..K.
5. **Apply granularity** — **all tuned stages at once**, with a per-stage change summary.
