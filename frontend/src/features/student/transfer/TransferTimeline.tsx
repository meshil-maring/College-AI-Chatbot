import type { TransferStatus, TransferAction } from '../../../types/transfer.ts';

const STATUS_ORDER: TransferStatus[] = [
  'submitted',
  'under_review',
  'eligible',
  'approved',
  'completed',
];

const STATUS_LABELS: Record<TransferStatus, string> = {
  submitted: 'Request Submitted',
  under_review: 'Under Review',
  eligible: 'Eligible',
  not_eligible: 'Not Eligible',
  approved: 'Approved',
  rejected: 'Rejected',
  completed: 'Completed',
  cancelled: 'Cancelled',
};

const STATUS_SUBTITLES: Record<TransferStatus, string> = {
  submitted: 'Your transfer request has been received.',
  under_review: 'Academic staff are reviewing your request.',
  eligible: 'Eligible for transfer — awaiting approval.',
  not_eligible: 'Not eligible — see review notes for details.',
  approved: 'Approved — awaiting completion.',
  rejected: 'Rejected — see rejection reason.',
  completed: 'Completed — your new placement is active.',
  cancelled: 'Cancelled.',
};

const STATUS_STAGE: Record<TransferStatus, number> = {
  submitted: 0,
  under_review: 1,
  eligible: 2,
  not_eligible: 1,
  approved: 3,
  completed: 4,
  rejected: 1,
  cancelled: 1,
};

function statusColor(status: TransferStatus): string {
  switch (status) {
    case 'submitted':
    case 'under_review':
    case 'eligible':
      return 'var(--ui-warning)';
    case 'approved':
    case 'completed':
      return 'var(--ui-success)';
    case 'rejected':
    case 'cancelled':
    case 'not_eligible':
      return 'var(--ui-danger)';
    default:
      return 'var(--ui-text-muted)';
  }
}

function statusBgColor(status: TransferStatus): string {
  switch (status) {
    case 'submitted':
    case 'under_review':
    case 'eligible':
      return 'var(--ui-warning-bg)';
    case 'approved':
    case 'completed':
      return 'var(--ui-success-bg)';
    case 'rejected':
    case 'cancelled':
    case 'not_eligible':
      return 'var(--ui-danger-bg)';
    default:
      return 'var(--ui-surface-raised)';
  }
}

interface TransferTimelineProps {
  status: TransferStatus | null;
  actions?: { action: TransferAction; created_at: string }[];
  submittedAt?: string | null;
}

export default function TransferTimeline({
  status,
  actions,
  submittedAt,
}: TransferTimelineProps) {
  const currentStage = status ? STATUS_STAGE[status] ?? 0 : 0;

  return (
    <section
      className="rounded-xl border border-line bg-surface p-4 sm:p-5"
      aria-label="Transfer timeline"
    >
      <div className="flex items-center justify-between gap-2 mb-4">
        <h2 className="font-semibold text-content text-section">Transfer Timeline</h2>
        <span className="ml-auto rounded-lg border border-line bg-surface-raised px-2 py-1 text-xs font-medium text-muted">
          {status ? STATUS_LABELS[status] : 'No status'}
        </span>
      </div>
      <ol className="relative space-y-6 pl-8">
        {STATUS_ORDER.map((stage, index) => {
          const isActive = status === stage;
          const isCompleted = currentStage > index;
          const isCurrent = currentStage === index;
          return (
            <li key={stage} className="relative group">
              <span
                className={`absolute -left-8 top-2 w-4 h-4 rounded-full border-2 flex items-center justify-center z-10 ${
                  isCompleted
                    ? 'border-success bg-success'
                    : isCurrent
                    ? 'border-accent bg-accent'
                    : 'border-line bg-surface'
                }`}
              >
                {isCompleted ? (
                  <span className="text-[10px] font-bold text-white">✓</span>
                ) : (
                  <span className="text-[10px] font-bold text-muted">○</span>
                )}
              </span>
              <div className="absolute -left-7.5 top-3.5 w-px h-full ${
                isCompleted ? 'bg-success' : 'border-line'
              }" />
              <div className="flex items-start gap-3">
                <div className="min-w-0">
                  <h3 className={`font-semibold text-content group-hover:text-accent ${isCurrent ? 'text-accent' : ''}`}>
                    {STATUS_LABELS[stage]}
                  </h3>
                  <p className={`text-sm ${isCompleted || isCurrent ? 'text-content' : 'text-muted'}`}>
                    {STATUS_SUBTITLES[stage]}
                  </p>
                </div>
                <span
                  className={`ml-auto shrink-0 rounded-lg border border-line bg-surface-raised px-2 py-1 text-xs font-medium ${isCurrent ? 'border-accent text-accent' : 'text-muted'}`}
                >
                  {submittedAt && index === 0 ? submittedAt : '—'}
                </span>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}