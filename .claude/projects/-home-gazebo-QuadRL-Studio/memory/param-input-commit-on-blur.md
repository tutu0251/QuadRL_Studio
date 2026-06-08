---
name: param-input-commit-on-blur
description: Convention — numeric/text param inputs across all editor frontends commit on blur/Enter, never per keystroke
metadata:
  type: project
---

All seven editor frontends (geometry-editor, physics-editor, control-editor, sensor-editor, rl-trainer-editor, ppo-planner, train-monitor) edit param values through inputs that hold a **local string draft while focused and commit only on blur or Enter** (Escape reverts). Do NOT bind a controlled input's `value` directly to server/store state with an `onChange` that writes through — that pattern fired a network PUT + full-model refetch per keystroke (slow) and coerced partial input like `0.0` / `-` / empty to `0` so decimals couldn't be typed.

**Why:** the user reported param entry was "very slow and difficult." Root cause was per-keystroke commit + controlled value snapback.

**How to apply:** route new numeric fields through the per-frontend primitive — `NumberField` (label + input wrapper) or the bare `NumericInput` (rl-trainer, physics, train-monitor); text fields through `TextField` (sensor-editor) or the `defaultValue`+`key`+`onBlur` pattern. Sliders update a local draft during drag and commit on `pointerUp`/`keyUp` (see [[#]] PoseEditorPanel's PoseJointRow). `nullable` NumericInput commits `null` on empty. Each primitive's commit signature is `onCommit`/`onChange: (v) => void`; props `value`/`step`/`min`/`max` unchanged so callers stay the same.
