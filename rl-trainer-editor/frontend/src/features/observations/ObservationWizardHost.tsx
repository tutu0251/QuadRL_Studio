import { useEffect, useState } from "react";
import type { ObservationTerm } from "@rl-trainer-model";
import { api } from "../../api/client";
import { useTrainerStore } from "../../stores/trainerStore";
import { ObservationSetupWizard, shouldShowObservationWizard } from "./ObservationSetupWizard";

const DEFAULT_N_JOINTS = 12;

export function ObservationWizardHost() {
  const project = useTrainerStore((s) => s.project);
  const model = useTrainerStore((s) => s.model);
  const open = useTrainerStore((s) => s.observationWizardOpen);
  const setOpen = useTrainerStore((s) => s.setObservationWizardOpen);
  const setModel = useTrainerStore((s) => s.setModel);
  const log = useTrainerStore((s) => s.log);
  const [nJoints, setNJoints] = useState(DEFAULT_N_JOINTS);

  useEffect(() => {
    if (!project || !open) return;
    let cancelled = false;
    api
      .getObservations(project)
      .then((summary) => {
        if (cancelled) return;
        if (summary.jointCount && summary.jointCount > 0) {
          setNJoints(summary.jointCount);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [project, open]);

  if (!open || !model || !project || !(model.observationTerms?.length ?? 0)) {
    return null;
  }

  const save = async (patch: Parameters<typeof api.patchModel>[1]) => {
    try {
      setModel(await api.patchModel(project, patch));
    } catch (e) {
      log(String(e));
    }
  };

  return (
    <ObservationSetupWizard
      terms={model.observationTerms}
      nJoints={nJoints}
      onConfirm={(terms: ObservationTerm[]) => {
        void save({ observationTerms: terms, observationsSetupComplete: true }).then(() => {
          setOpen(false);
          log("Observation vector confirmed");
        });
      }}
      onDismiss={() => {
        void save({ observationWizardDismissed: true }).then(() => {
          setOpen(false);
          log("Observation setup wizard dismissed — use Observations tab to edit");
        });
      }}
    />
  );
}

export function openObservationWizardIfNeeded(model: Parameters<typeof shouldShowObservationWizard>[0]) {
  if (shouldShowObservationWizard(model)) {
    useTrainerStore.getState().setObservationWizardOpen(true);
  }
}
