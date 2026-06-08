import { getApiBaseUrl, tbOpenUrl } from "../../api/client";
import { ActionButton } from "../../components/ActionButton";
import type { TensorBoardStatus } from "../../types";

type Props = {
  project: string | null;
  tbStatus: TensorBoardStatus | null;
  busy: boolean;
  onOpenTb: () => void;
  onStopTb: () => void;
  tbStartCommand?: string | null;
  tbStopCommand?: string | null;
  tbStartLoading?: boolean;
  tbStopLoading?: boolean;
};

export function TensorBoardPanel({
  project,
  tbStatus,
  busy,
  onOpenTb,
  onStopTb,
  tbStartCommand,
  tbStopCommand,
  tbStartLoading,
  tbStopLoading,
}: Props) {
  const tbLink =
    project && tbStatus?.running
      ? `${getApiBaseUrl()}${tbStatus.open_url ?? tbOpenUrl(project)}`
      : null;

  return (
    <section className="panel tb-panel">
      <header className="panel-header">
        <h2>
          TensorBoard
          <span className={`live-dot ${tbStatus?.running ? "on" : ""}`} title={tbStatus?.running ? "Running" : "Stopped"} />
        </h2>
      </header>

      <div className="btn-row metrics-tb-actions">
        {!tbStatus?.running ? (
          <ActionButton
            className="btn small accent"
            disabled={busy || !project}
            command={tbStartCommand}
            commandLoading={tbStartLoading}
            onClick={onOpenTb}
          >
            Launch TensorBoard
          </ActionButton>
        ) : (
          <>
            {tbLink && (
              <a className="btn small link accent" href={tbLink} target="_blank" rel="noreferrer">
                Open TensorBoard
              </a>
            )}
            <ActionButton
              className="btn small ghost"
              disabled={busy}
              command={tbStopCommand}
              commandLoading={tbStopLoading}
              onClick={onStopTb}
            >
              Stop TB
            </ActionButton>
          </>
        )}
      </div>

      {tbStatus?.error && <p className="panel-warn">{tbStatus.error}</p>}
    </section>
  );
}
