# PPO Planner

Web-based planner for PPO (stable-baselines3-style) hyperparameters. Profiles the host machine (CPU, RAM, GPU) and recommends rollout batch sizes, parallel envs, and device settings. Exports `ppo_<project>_config.yaml` into the shared project folder.

**DEV MODE:** No authentication. Bind `0.0.0.0` for LAN use only.

## Quick start

```bash
cd /home/gazebo/QuadRL_Studio
chmod +x start_ppo_planner.sh ppo-planner/start_*.sh
./start_ppo_planner.sh
```

Browser: `http://<host>:5177`

## Workflow

1. Complete the four-editor pipeline (geometry → physics → control → sensor) for your robot, or create a project folder under `~/quadruped_dev_tool/projects/<name>/`.
2. In **PPO Planner**, select the project (File menu) — loading bootstraps `ppo_model.json` with machine-based recommendations.
3. Adjust hyperparameters in the inspector, or click **Recommend** to re-profile the host.
4. **Validate** → **Export YAML** → `exports/ppo_<name>_config.yaml`

## Ports

| Service  | Port |
|----------|------|
| Backend  | 8004 |
| Frontend | 5177 |

## Storage

```
~/quadruped_dev_tool/projects/<project_name>/
  ppo_model.json
  exports/ppo_<name>_config.yaml
```

## Recommendation rules (summary)

| Signal | Effect |
|--------|--------|
| RAM &lt; 8 GB | Smaller `n_steps`, `batch_size`, single env |
| RAM 16–32 GB | Larger batch, up to 4 parallel envs |
| RAM ≥ 32 GB | `n_steps=4096`, batch up to 256, up to 8 envs |
| NVIDIA GPU | `device=cuda`, batch/env scaling by VRAM |
| No GPU | `device=cpu`, capped batch and env count |

`batch_size` is adjusted so `n_steps × num_envs` divides evenly (SB3-friendly).

## Shared types

`packages/ppo-model/` — TypeScript types for the frontend.

## Tests

```bash
cd ppo-planner/backend && python3 -m pytest ../tests -q
```
