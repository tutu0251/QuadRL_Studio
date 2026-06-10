"""Optuna + Claude training-parameter tuning engine.

A thin orchestration layer over the existing training launcher
(``training/scripts/run_rl_train.py``): Optuna drives the numeric trials, and
Claude is invoked every N trials to review ``study.trials_dataframe()`` and
decide whether to adjust reward weights, re-center the search space, or stop.
"""
