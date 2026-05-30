# RL Trainer Editor

Configure quadruped RL training for **Stable-Baselines3 + ROS 2 / Gazebo**: task rewards/penalties, termination thresholds, PPO hyperparameters, parallel env settings, and custom parameters.

## Quick start

```bash
chmod +x start_*.sh
./start_rl_trainer_editor.sh
```

- Backend API: `http://0.0.0.0:8005`
- Frontend UI: `http://0.0.0.0:5178`

## Prerequisites

Complete the sensor editor pipeline first (`sensor_model.json` and `sens_*_observations.yaml`). The trainer editor reads the same project folder as other QuadRL tools:

`~/quadruped_dev_tool/projects/<name>/`

## Workflow

1. **File → select project** — auto-bootstraps with `velocity_tracking` preset + machine recommendations.
2. **Curriculum** — for step-by-step training, apply **Stand still → Sprint**: stand → slow walk → walk → run → sprint (~2.1M steps total). Each stage has its own rewards, velocity command, and advance criteria.
3. **Presets** — pick velocity tracking, stand still, efficient locomotion, or custom blank.
3. **Recommend** — tune `num_envs`, batch sizes, and device from CPU/RAM/GPU profile.
4. **Rewards / Termination / Hyperparams / Parallel / Custom** — adjust manually; disable auto-apply to keep overrides when re-recommending.
5. **Validate → Export YAML** — writes `exports/rl_<project>_config.yaml`.
6. **Start training** — validates, exports config, and launches PPO (curriculum stages run in order). Logs stream to the console; checkpoints go to `checkpoints/` in the project folder. TensorBoard scalars go to `runs/<timestamp>/` (curriculum stages use subfolders).

### Training dependencies (optional)

For real SB3 training (not dry-run simulation):

```bash
cd /home/gazebo/QuadRL_Studio/training
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

If `gymnasium` / `stable-baselines3` are missing, the launcher falls back to a short dry-run progress simulation. Set `QUADRL_TRAIN_DRY_RUN=1` to force dry-run.

### TensorBoard

Each training run writes TensorBoard event files under the project folder:

```
~/quadruped_dev_tool/projects/<name>/runs/
  <YYYYMMDD_HHMMSS>/
    run_info.yaml
    training/              # single-stage run (SB3 creates PPO_1/ inside)
    01_<stage_id>_<name>/  # curriculum stage (one subfolder per stage)
```

**From the UI:** load a project and click **TensorBoard** in the toolbar. The backend starts TensorBoard on port 6006 (bound to `0.0.0.0` via `--bind_all`) and opens a browser tab to the correct host. The console shows a clickable URL.

**Remote / SSH access:** open the trainer UI using the machine IP or hostname (e.g. `http://192.168.1.10:5178`), not `localhost`. TensorBoard will be reachable at `http://<same-host>:6006`. Ensure port 6006 is allowed through your firewall. Optionally set `TB_PUBLIC_HOST=<hostname>` if you use a reverse proxy and need a fixed public hostname in links.

**CLI:**

```bash
tensorboard --logdir ~/quadruped_dev_tool/projects/<project>/runs --bind_all --port 6006
```

Open `http://<machine-ip-or-hostname>:6006` in your browser (not `localhost` unless the browser runs on the same machine).

The exported `rl_<project>_config.yaml` includes a `logging.tensorboard_root: runs` field documenting the relative log root.

## Export contract

The unified YAML references existing exports:

| Field | File |
|-------|------|
| `env.observations_file` | `sens_<project>_observations.yaml` |
| `env.gains_file` | `ctrl_<project>_gains.yaml` |
| `env.sim_urdf` | `sens_<project>_rl.urdf` |

Your SB3 + ROS2 env loader should:

- Map `task.reward_terms` to shaped scalars each step
- Apply `task.termination` for done/truncation
- Construct `PPO` from `hyperparameters` and `VecEnv` with `parallel.num_envs`
- When `curriculum.enabled` is true, iterate `curriculum.stages` in order: train `timesteps` per stage, check `advance_criteria`, optionally load the previous checkpoint (`load_previous_checkpoint`), then switch `reward_terms` and `command` for the next stage

`custom_params` is exported verbatim for forward-compatible extensions.

## PPO Planner

[PPO Planner](../ppo-planner/) remains available for hyperparameter-only tuning. New projects should use `rl_*_config.yaml` as the canonical trainer contract.

## Tests

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
PYTHONPATH=backend .venv/bin/pytest tests/ -q
```
