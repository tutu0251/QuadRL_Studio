/**
 * Friendly, consistent naming for every parameter the Training Predictor exposes.
 *
 * The backend speaks in cryptic, namespaced keys (`hp.learning_rate`, `rw.upright`,
 * `rp.upright.sigma`) and snake_case request fields (`advisor_every_n`, `mock_objective`).
 * This module is the single place that turns those into kind, Title-Case labels for the UI
 * — while preserving the raw key as a mono sublabel so engineers can still cross-reference.
 *
 * Consistency: PPO hyperparameter tooltips are pulled verbatim from the shared
 * `@ppo-model` source of truth (the same wording the PPO Planner shows), so a given
 * parameter reads identically everywhere in QuadRL Studio.
 */
import { PPO_PARAM_HINTS } from "@ppo-model";
import type { PpoHyperparams } from "@ppo-model";

export interface FieldMeta {
  /** Friendly Title-Case name shown to the user. */
  label: string;
  /** The raw backend key, shown as a small mono sublabel. */
  code: string;
  /** Tooltip help text. */
  hint?: string;
}

/** Title-case a snake_case / kebab id: `forward_velocity` -> `Forward Velocity`. */
export function humanize(id: string): string {
  return id
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** hp.<name> -> friendly label + the canonical @ppo-model hint key. */
const HP_LABELS: Record<string, { label: string; hintKey?: keyof PpoHyperparams; hint?: string }> = {
  learning_rate: { label: "Learning Rate", hintKey: "learningRate" },
  ent_coef: { label: "Entropy Coefficient", hintKey: "entCoef" },
  clip_range: { label: "Clip Range", hintKey: "clipRange" },
  gamma: { label: "Discount Factor (γ)", hintKey: "gamma" },
  gae_lambda: { label: "GAE Lambda (λ)", hintKey: "gaeLambda" },
  vf_coef: { label: "Value-Function Coefficient", hintKey: "vfCoef" },
  n_epochs: { label: "Epochs per Update", hintKey: "nEpochs" },
  batch_size: { label: "Batch Size", hintKey: "batchSize" },
  n_steps: { label: "Steps per Rollout", hintKey: "nSteps" },
};

/** Friendly names for reward-term shaping params (the `<param>` in `rp.<id>.<param>`). */
const REWARD_PARAM_LABELS: Record<string, { label: string; hint: string }> = {
  sigma: {
    label: "Tolerance (σ)",
    hint: "Width of the reward's tolerance band — larger σ is more forgiving",
  },
};

/**
 * Describe any namespaced search-space / trial parameter key.
 * Handles PPO hyperparameters (`hp.*`), reward weights (`rw.<id>`) and
 * reward shaping params (`rp.<id>.<param>`); falls back gracefully for anything else.
 */
export function describeParam(key: string): FieldMeta {
  if (key.startsWith("hp.")) {
    const name = key.slice(3);
    const m = HP_LABELS[name];
    if (m) {
      return { label: m.label, code: key, hint: m.hintKey ? PPO_PARAM_HINTS[m.hintKey] : m.hint };
    }
    return { label: humanize(name), code: key };
  }
  if (key.startsWith("rw.")) {
    const id = key.slice(3);
    return {
      label: `${humanize(id)} — Reward Weight`,
      code: key,
      hint: `How strongly the “${id}” reward term counts (penalties keep their sign)`,
    };
  }
  if (key.startsWith("rp.")) {
    const rest = key.slice(3);
    const dot = rest.indexOf(".");
    const id = dot >= 0 ? rest.slice(0, dot) : rest;
    const param = dot >= 0 ? rest.slice(dot + 1) : "";
    const pm = REWARD_PARAM_LABELS[param];
    return {
      label: `${humanize(id)} — ${pm ? pm.label : humanize(param)}`,
      code: key,
      hint: pm ? pm.hint : `Shaping parameter “${param}” for the “${id}” reward term`,
    };
  }
  return { label: humanize(key), code: key };
}

/** Setup-form field keys that carry their own friendly metadata. */
export type SetupKey =
  | "study_name"
  | "n_trials"
  | "advisor_every_n"
  | "trial_timesteps"
  | "trial_timeout"
  | "gazebo_headless"
  | "max_stages"
  | "monitor_base_url"
  | "mock_objective"
  | "include_hyperparams"
  | "include_reward_weights"
  | "include_reward_params";

/** Friendly labels + help for the tuning request fields (StartTuningRequest). */
export const SETUP_FIELDS: Record<SetupKey, FieldMeta> = {
  study_name: {
    label: "Resume Study",
    code: "study_name",
    hint: "Continue a previous study for this project — its trials and best-so-far carry over, and new trials run until the target total is reached. “New study” starts fresh.",
  },
  n_trials: {
    label: "Trials to Run",
    code: "n_trials",
    hint: "How many training trials the optimizer will run in this study",
  },
  advisor_every_n: {
    label: "Ask Claude Every N Trials",
    code: "advisor_every_n",
    hint: "How often Claude reviews progress and re-centers the search",
  },
  trial_timesteps: {
    label: "Timesteps per Trial",
    code: "trial_timesteps",
    hint: "Short training budget for each trial — a fast proxy for full training",
  },
  trial_timeout: {
    label: "Per-Trial Time Limit",
    code: "trial_timeout",
    hint: "Give up on a trial after this many seconds (leave blank for no limit)",
  },
  gazebo_headless: {
    label: "Run Simulator Headless",
    code: "gazebo_headless",
    hint: "Train without the Gazebo window — faster and lighter",
  },
  max_stages: {
    label: "Train Up To Stage",
    code: "max_stages",
    hint: "Train the curriculum from the start up to and including this stage — a faster proxy than the full curriculum. “All stages” uses the whole curriculum.",
  },
  monitor_base_url: {
    label: "Train Monitor Address",
    code: "monitor_base_url",
    hint: "Where the Train Monitor API runs — blank uses the default (port 8006)",
  },
  mock_objective: {
    label: "Practice Run (no real training)",
    code: "mock_objective",
    hint: "Use synthetic scores to test the loop end-to-end without training anything",
  },
  include_hyperparams: {
    label: "Tune PPO Hyperparameters",
    code: "include_hyperparams",
    hint: "Let the optimizer explore learning rate, clip range, and friends",
  },
  include_reward_weights: {
    label: "Tune Reward Weights",
    code: "include_reward_weights",
    hint: "Let the optimizer rebalance how much each reward term counts",
  },
  include_reward_params: {
    label: "Tune Reward Shaping",
    code: "include_reward_params",
    hint: "Let the optimizer adjust reward shaping params like tolerance (σ)",
  },
};

/** Human label for a study lifecycle state. */
export const STATE_LABELS: Record<string, string> = {
  pending: "Getting ready",
  running: "Running",
  complete: "Complete",
  stopped: "Stopped",
  error: "Error",
};
