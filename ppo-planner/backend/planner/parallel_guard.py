"""Normalize and validate parallel training settings."""
from __future__ import annotations

from domain.models import MachineProfile, ParallelConfig, VecEnvType


def max_recommended_envs(machine: MachineProfile | None) -> int:
    """Upper bound for num_envs based on host resources."""
    if not machine:
        return 8
    physical = max(1, machine.cpuCountPhysical)
    ram = machine.ramGb or 8.0
    if ram < 8:
        return 1
    if ram < 16:
        return min(2, max(1, physical // 4))
    if ram < 32:
        return min(4, max(1, physical // 2))
    cap = min(8, max(2, physical // 2))
    if machine.gpuAvailable and machine.vramGb >= 12:
        logical = max(1, machine.cpuCountLogical)
        cap = min(8, max(cap, min(4, logical // 2)))
    if not machine.gpuAvailable:
        cap = min(cap, max(1, physical // 2))
    return max(1, cap)


def normalize_parallel_config(
    parallel: ParallelConfig,
    *,
    physical_cores: int,
) -> tuple[ParallelConfig, list[str]]:
    """Apply safe defaults and resolve common parallelization conflicts."""
    notes: list[str] = []
    par = parallel.model_copy(deep=True)
    physical = max(1, physical_cores)

    if par.numEnvs < 1:
        par.numEnvs = 1
        notes.append("Raised num_envs to 1 (minimum).")

    if par.numEnvs == 1 and par.vecEnvType == VecEnvType.SUBPROC:
        par.vecEnvType = VecEnvType.DUMMY
        par.nProc = None
        notes.append("Switched to dummy vec env — subproc adds overhead for a single env.")

    if par.vecEnvType == VecEnvType.DUMMY:
        if par.nProc is not None:
            par.nProc = None
            notes.append("Cleared n_proc — not used with dummy vec env.")
    else:
        if par.nProc is None:
            par.nProc = min(physical, par.numEnvs)
        elif par.nProc > par.numEnvs:
            par.nProc = par.numEnvs
            notes.append(f"Capped n_proc to num_envs ({par.numEnvs}).")
        elif par.nProc > physical:
            par.nProc = physical
            notes.append(f"Capped n_proc to physical CPU cores ({physical}).")

    return par, notes


def parallel_validation_issues(
    parallel: ParallelConfig,
    *,
    machine: MachineProfile | None,
    physical_cores: int,
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) message lists for parallel config."""
    errors: list[str] = []
    warnings: list[str] = []
    physical = max(1, physical_cores)
    par = parallel

    if par.numEnvs < 1:
        errors.append("num_envs must be at least 1.")

    if par.vecEnvType == VecEnvType.DUMMY and par.nProc is not None:
        errors.append("n_proc must be unset when vec_env_type is dummy.")

    if par.vecEnvType == VecEnvType.SUBPROC:
        if par.numEnvs == 1:
            warnings.append(
                "subproc with num_envs=1 adds process overhead; prefer dummy vec env."
            )
        if par.nProc is not None:
            if par.nProc > par.numEnvs:
                errors.append(
                    f"n_proc ({par.nProc}) cannot exceed num_envs ({par.numEnvs})."
                )
            if par.nProc > physical:
                warnings.append(
                    f"n_proc ({par.nProc}) exceeds physical CPU cores ({physical}); "
                    "may oversubscribe the host."
                )
        if par.numEnvs > physical:
            warnings.append(
                f"num_envs ({par.numEnvs}) exceeds physical cores ({physical}); "
                "sim instances may contend for CPU."
            )

    if machine:
        recommended = max_recommended_envs(machine)
        if par.numEnvs > recommended:
            warnings.append(
                f"num_envs ({par.numEnvs}) exceeds recommended maximum ({recommended}) "
                f"for {machine.ramGb:.1f} GB RAM and {physical} physical cores."
            )

    return errors, warnings
