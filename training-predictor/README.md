# Training Predictor — User Guide

The **Training Predictor** searches for good PPO training settings for a quadruped
project, so you don't have to hand-tune them. It runs many short "trial" trainings,
scores each one, and **Optuna** steers the search toward better numbers. Every few
trials, **Claude** reviews the progress and re-centers the search, rebalances reward
weights, or stops early. When you're happy, one click writes the best settings back
into your project's config files.

> **In one line:** Optuna explores the numbers, Claude steers the search, you press
> *Start* and then *Save to project*.

---

## Contents

1. [How it works](#how-it-works)
2. [Prerequisites](#prerequisites)
3. [Starting it up](#starting-it-up)
4. [The workflow, step by step](#the-workflow-step-by-step)
5. [**The Study Setup panel — every parameter explained**](#the-study-setup-panel--every-parameter-explained)
6. [What actually gets tuned (the search space)](#what-actually-gets-tuned-the-search-space)
7. [Reading the results](#reading-the-results)
8. [Saving the best settings to your project](#saving-the-best-settings-to-your-project)
9. [Recommended recipes](#recommended-recipes)
10. [Troubleshooting](#troubleshooting)

---

## How it works

Each **trial** is a short training run with one specific combination of settings.

```
  ┌─ you press Start ─────────────────────────────────────────────┐
  │                                                                │
  │   Optuna picks settings  ─►  short training (Train Monitor)    │
  │          ▲                          │                          │
  │          │                          ▼                          │
  │   apply Claude's advice    score the run (mean episode reward) │
  │          ▲                          │                          │
  │          └──── every N trials ──────┘                          │
  │              Claude reviews & steers                           │
  └────────────────────────────────────────────────────────────────┘
```

- The **objective** each trial is scored on is the **mean episode reward**
  (`eval/mean_reward`, falling back to `rollout/ep_rew_mean`) read from the run's
  TensorBoard logs. **Higher is better.**
- Real trials are trained through the **Train Monitor** (the single training
  controller, port `8006`). The Training Predictor never launches training itself.
- After the study, the **best trial's** settings can be written back into your
  project's PPO and RL config files (originals are backed up).

---

## Prerequisites

| Need | Why | How |
|---|---|---|
| **Training Predictor backend** on `:8007` | Serves the API the UI talks to | `training-predictor/start_backend.sh` |
| **Train Monitor** on `:8006` | Runs the real trainings | start it before a real study (not needed for a Practice Run) |
| **A project with exports** | Provides the base configs to tune | needs `exports/rl_<project>_config.yaml` under your projects root |
| **Claude advisor** *(optional)* | Steers the search every N trials | works with **no API key** via the Claude Code CLI — see below |

### The Claude advisor needs no API key

The advisor has two backends and auto-selects:

- **API key present** (`ANTHROPIC_API_KEY` in the repo-root `.env`) → uses the Anthropic API.
- **No API key** → uses the local **Claude Code CLI**, authenticated by your Claude
  Code (Max/Pro) login. `start_backend.sh` locates the CLI automatically.
- **Neither available** → the study still runs as **pure Optuna** (no Claude steering);
  everything else works.

Check the top-bar **Claude** chip: green means the advisor is active. The backend also
prints its choice on startup (`advisor: Claude via CLI … — no API key needed`).

---

## Starting it up

```bash
# from the repo root
./training-predictor/start_backend.sh     # API on :8007 (installs its own venv on first run)
./training-predictor/start_frontend.sh    # UI  on :5180
```

…or start everything at once with `./start_all.sh` (or `./start_all_headless.sh`),
which now includes the Training Predictor. Then open **http://<host>:5180**.

The UI talks to the backend at `http://127.0.0.1:8007` by default; override with
`VITE_API_BASE_URL` (the start script sets this for you from `TRAINING_PREDICTOR_PORT`).

---

## The workflow, step by step

1. **Pick a project** in the top bar. Only projects with an RL export show up.
2. **Configure the study** in the *Study setup* panel (left). Defaults are sensible — for
   your first run, just turn on **Practice Run** to see the loop work end-to-end.
3. **Press *Start study*.** Settings lock while it runs.
4. **Watch** the *Best so far*, *Trials*, *Claude's insights*, and *Live log* panels update.
5. **Press *Save to project*** to write the best trial's settings into your config files,
   or **Stop** at any time.

---

## The Study Setup panel — every parameter explained

Each field shows a **friendly name**, the **raw config key** beneath it (in mono), and an
**ⓘ tooltip**. The panel is grouped into *The run*, *Simulation*, and *What to tune*.
All fields are **locked while a study is running.**

### Group 1 — The run

| Field | Key | Default | Range | What it does | Guidance |
|---|---|---|---|---|---|
| **Trials to Run** | `n_trials` | `20` | 1–1000 | How many trial trainings the study will run in total. | More trials = a better search but more wall-clock time. 20–40 is a reasonable real run; 5–10 for a quick look. |
| **Ask Claude Every N Trials** | `advisor_every_n` | `5` | ≥ 1 | How often Claude pauses to review progress and steer the search (re-center ranges, rebalance rewards, or stop early). | Smaller = more frequent steering (and more advisor calls). With few trials, keep this at 3–5 so Claude gets at least a couple of chances. Claude is **not** consulted after the final trial. |
| **Timesteps per Trial** | `trial_timesteps` | `30000` | ≥ 1 (step 1000) | The **short training budget** for each trial — a fast *proxy* for full training. For curriculum projects it is spread across the stages in proportion to their original lengths (with a one-rollout floor per stage). | This is the main speed↔signal dial. Too small and scores are noisy; too big and each trial is slow. 20k–50k is a good proxy range; raise it if scores look random. |
| **Per-Trial Time Limit** | `trial_timeout` | *(blank)* | seconds, optional | Give up on a single trial after this many seconds. Blank = no limit. | Use it as a safety net so one stuck trial can't stall the whole study. Set it comfortably above how long a healthy trial takes. |

### Group 2 — Simulation

| Field | Key | Default | What it does | Guidance |
|---|---|---|---|---|
| **Run Simulator Headless** | `gazebo_headless` | **On** | Trains without opening the Gazebo window. | Leave **on** for tuning — it's faster and lighter, and you don't need to watch each trial. |
| **Practice Run (no real training)** | `mock_objective` | Off | Scores trials with a cheap **synthetic** function instead of training anything. Lets you exercise the whole loop (Optuna + Claude + the UI) in seconds. | Turn **on** for your first run or after changing settings — it needs **no Train Monitor and no GPU**. Turn **off** for a real study. |
| **Curriculum Stages to Use** | `max_stages` | *(blank = all)* | For curriculum projects, train only the **first N** stages per trial. Blank uses all stages, scaled to the budget. | Set to `1`–`2` to tune just the early stages quickly; leave blank to tune the full curriculum. Ignored for non-curriculum projects. |
| **Train Monitor Address** | `monitor_base_url` | *(blank = default)* | Where the Train Monitor API lives. Blank uses the default (`http://127.0.0.1:8006`). | Only set this if your Train Monitor runs on another host/port. Not used during a Practice Run. |

### Group 3 — What to tune

These three switches decide **which kinds of settings Optuna is allowed to explore**.
At least one should be on. See the next section for exactly what each one expands into.

| Field | Key | Default | What it does | Guidance |
|---|---|---|---|---|
| **Tune PPO Hyperparameters** | `include_hyperparams` | On | Lets Optuna vary the PPO learning settings (learning rate, clip range, etc.). | Keep on — these usually have the biggest impact on learning stability. |
| **Tune Reward Weights** | `include_reward_weights` | On | Lets Optuna rebalance **how strongly each reward term counts** for your task. | Keep on if your robot's *behavior* (not just learning speed) needs work — e.g. it falls over or won't walk. |
| **Tune Reward Shaping** | `include_reward_params` | On | Lets Optuna adjust reward **shaping** parameters — currently each term's tolerance **σ** (how forgiving that term is). | Leave on for fine behavior tuning; turn off to keep the search smaller and faster. |

> **Tip:** turning a switch off shrinks the search space, so the same number of trials
> explores the remaining settings more thoroughly. For a focused study, tune one kind at a time.

---

## What actually gets tuned (the search space)

The three *What to tune* switches expand into the concrete parameters Optuna samples.
The friendly names below are exactly what you'll see in *Best so far* and *Trials*.

### PPO hyperparameters (`include_hyperparams`)

| Friendly name | Key | Search range |
|---|---|---|
| Learning Rate | `hp.learning_rate` | 1e-5 … 1e-3 (log scale) |
| Entropy Coefficient | `hp.ent_coef` | 1e-4 … 5e-2 (log scale) |
| Clip Range | `hp.clip_range` | 0.10 … 0.40 |
| Discount Factor (γ) | `hp.gamma` | 0.95 … 0.999 |
| GAE Lambda (λ) | `hp.gae_lambda` | 0.90 … 0.99 |
| Value-Function Coefficient | `hp.vf_coef` | 0.30 … 1.00 |
| Epochs per Update | `hp.n_epochs` | 5 … 20 |
| Batch Size | `hp.batch_size` | 32 / 64 / 128 / 256 |
| Steps per Rollout | `hp.n_steps` | 1024 / 2048 / 4096 |

The PPO parameter tooltips match the wording used in the **PPO Planner**, so a given
setting reads the same everywhere in QuadRL Studio.

### Reward weights (`include_reward_weights`)

For each **enabled** reward term in your project, Optuna explores its weight from
`0` up to about **2× its current magnitude** (the sign — reward vs. penalty — is kept
from your base config). Shown as e.g. **"Upright — Reward Weight"** (`rw.upright`).

### Reward shaping (`include_reward_params`)

For each term that has a tolerance **σ**, Optuna explores it from about **0.4×** to
**2.5×** its current value. Shown as e.g. **"Upright — Tolerance (σ)"** (`rp.upright.sigma`).
A **smaller σ makes a term sharper / less forgiving**; a larger σ is more lenient.

---

## Reading the results

- **Best so far** — a progress bar (`done / total` trials), the leading **objective**
  score, and that trial's predicted settings (friendly names + raw keys). The
  **Save to project** button lives here.
- **Trials** — every trial, newest first: number, state, objective, and its settings as
  chips. The current best row is highlighted.
- **Claude's insights** — what the advisor decided after each review and **why**, with
  any re-centered ranges shown as `before → after`. Empty if the advisor is disabled.
- **Live log** — the streamed study log (trial starts, scores, advisor actions),
  color-coded by level.

---

## Saving the best settings to your project

Pressing **Save to project** (with a best trial available) writes the winning settings
into the **same files your editors and the Train Monitor read**:

- **PPO hyperparameters** (`hp.*`) → `exports/ppo_<project>_config.yaml` (or the RL
  config's `hyperparameters` block if there's no PPO export).
- **Reward weights & shaping** (`rw.* / rp.*`) → `exports/rl_<project>_config.yaml`
  under `task.reward_terms`.

**Every edited file is backed up first** as `<file>.bak-<timestamp>`, and the UI reports
exactly what changed and which backups were made. You'll be asked to confirm before anything is written.

---

## Recommended recipes

**First time / smoke test (seconds, no GPU, no Train Monitor):**
- Practice Run **on**, Trials `10`, Ask Claude Every `3`. Press Start and watch the loop,
  the best score climb, and Claude's insights appear.

**Real tuning run:**
- Practice Run **off**, Train Monitor running on `:8006`, Run Simulator Headless **on**.
- Trials `20`–`40`, Timesteps per Trial `30000`–`50000`, Ask Claude Every `5`.
- Set a Per-Trial Time Limit as a safety net.

**Focused behavior fix (robot falls / won't walk):**
- Tune PPO Hyperparameters **off**, Tune Reward Weights **on**, Tune Reward Shaping **on**.
- Fewer dimensions → the trial budget digs deeper into the reward balance.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Top bar shows **API offline** | Backend not running | `./training-predictor/start_backend.sh` (API on `:8007`) |
| **Claude disabled** chip | No API key **and** the Claude Code CLI wasn't found | Log in to Claude Code, or set `QUADRL_CLAUDE_CLI` to the binary; or add `ANTHROPIC_API_KEY` to the repo-root `.env`. The study still runs without it (pure Optuna). |
| **Monitor offline** chip / start fails on a real study | Train Monitor not reachable | Start the Train Monitor on `:8006`, or set **Train Monitor Address** — or use a Practice Run. |
| Project missing from the picker | No RL export | The project needs `exports/rl_<project>_config.yaml` under your projects root. |
| Objective scores look random | Trial budget too small | Raise **Timesteps per Trial**. |
| "no TensorBoard event files / objective not found" | The trial's training didn't produce eval logs | Confirm the Train Monitor trains and logs `eval/mean_reward` (or `rollout/ep_rew_mean`). |
