import { useState } from 'react';
import { ArrowLeftRight, Plus, X } from 'lucide-react';
import { useAuth } from '../../auth/session/AuthProvider.tsx';
import { useMyTransferRequests, useMyTransferRequest, useInstitutionTransferSettings } from '../transfer/useStudentTransfers.ts';
import TransferForm from '../transfer/TransferForm.tsx';
import TransferTimeline from '../transfer/TransferTimeline.tsx';
import type { TransferStatus, TransferAction } from '../../../types/transfer.ts';

const STATUS_BADGE: Record<TransferStatus, string> = {
  submitted: 'bg-warning/10 text-warning border-warning/30',
  under_review: 'bg-warning/10 text-warning border-warning/30',
  eligible: 'bg-success/10 text-success border-success/30',
  not_eligible: 'bg-danger/10 text-danger border-danger/30',
  approved: 'bg-success/10 text-success border-success/30',
  rejected: 'bg-danger/10 text-danger border-danger/30',
  completed: 'bg-success/10 text-success border-success/30',
  cancelled: 'bg-muted/10 text-muted border-line',
};

const STATUS_LABEL: Record<TransferStatus, string> = {
  submitted: 'Submitted',
  under_review: 'Under Review',
  eligible: 'Eligible',
  not_eligible: 'Not Eligible',
  approved: 'Approved',
  rejected: 'Rejected',
  completed: 'Completed',
  cancelled: 'Cancelled',
};

function TransferDetail({ requestId, onBack }: { requestId: string; onBack: () => void }) {
  const { accessToken } = useAuth();
  const { data, isLoading, isError } = useMyTransferRequest(accessToken as string, requestId);

  if (isLoading) {
    return <p className="text-sm text-muted py-8 text-center">Loading transfer details…</p>;
  }
  if (isError || !data) {
    return <p className="text-sm text-danger py-8 text-center">Could not load transfer request.</p>;
  }

  const { request, actions } = data;
  const actionHistory = (actions ?? []) as { action: TransferAction; created_at: string }[];

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-muted hover:text-content transition-colors"
      >
        <X size={14} /> Back to list
      </button>

      <div className="rounded-xl border border-line bg-surface p-4 sm:p-5 space-y-3">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <h2 className="font-semibold text-content text-section">
              {request.transfer_type === 'section_transfer' ? 'Section Transfer' : 'Program Transfer'}
            </h2>
            <p className="text-xs text-muted mt-0.5">ID: {request.request_id}</p>
          </div>
          <span className={`rounded-lg border px-2 py-1 text-xs font-medium ${STATUS_BADGE[request.status]}`}>
            {STATUS_LABEL[request.status]}
          </span>
        </div>
        <p className="text-sm text-content">{request.reason}</p>
        {request.eligibility_notes && (
          <p className="text-xs text-muted border-t border-line pt-3">{request.eligibility_notes}</p>
        )}
        {request.rejection_reason && (
          <p className="text-xs text-danger border-t border-line pt-3">
            Rejection reason: {request.rejection_reason}
          </p>
        )}
      </div>

      <TransferTimeline
        status={request.status}
        actions={actionHistory}
        submittedAt={request.created_at ? new Date(request.created_at).toLocaleDateString() : null}
      />
    </div>
  );
}

export default function TransferRequestsPage() {
  const { accessToken } = useAuth();
  const [showForm, setShowForm] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: settings } = useInstitutionTransferSettings(accessToken as string);
  const { data: list, isLoading, isError, refetch } = useMyTransferRequests(accessToken as string);

  const canSubmit = settings?.allow_student_transfer_requests ?? false;
  const items = list?.items ?? [];

  if (selectedId) {
    return <TransferDetail requestId={selectedId} onBack={() => setSelectedId(null)} />;
  }

  if (showForm) {
    return (
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => setShowForm(false)}
          className="flex items-center gap-1.5 text-sm text-muted hover:text-content transition-colors"
        >
          <X size={14} /> Cancel
        </button>
        <TransferForm
          currentPlacement={null}
          targetPrograms={[]}
          targetSemesters={[]}
          targetSections={[]}
          onSuccess={() => {
            setShowForm(false);
            void refetch();
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted">
          {canSubmit
            ? 'Submit and track your academic transfer requests.'
            : 'Transfer requests are managed by your institution. Contact your administrator.'}
        </p>
        {canSubmit && (
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent shrink-0"
          >
            <Plus size={15} /> New Request
          </button>
        )}
      </div>

      {isLoading && (
        <p className="text-sm text-muted text-center py-10">Loading transfer requests…</p>
      )}

      {isError && (
        <p className="text-sm text-danger text-center py-10">
          Could not load transfer requests. Please try again.
        </p>
      )}

      {!isLoading && !isError && items.length === 0 && (
        <div className="rounded-xl border border-line bg-surface p-8 text-center">
          <ArrowLeftRight size={32} className="mx-auto text-muted mb-3" />
          <p className="text-sm text-muted">No transfer requests yet.</p>
        </div>
      )}

      {items.length > 0 && (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.request_id}>
              <button
                type="button"
                onClick={() => setSelectedId(item.request_id)}
                className="w-full text-left rounded-xl border border-line bg-surface p-4 hover:bg-surface-hover transition-colors focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <p className="font-medium text-content text-sm">
                      {item.transfer_type === 'section_transfer' ? 'Section Transfer' : 'Program Transfer'}
                    </p>
                    {item.current_program_name && (
                      <p className="text-xs text-muted mt-0.5 truncate">
                        {item.current_program_name}
                        {item.target_program_name && item.target_program_name !== item.current_program_name
                          ? ` → ${item.target_program_name}`
                          : ''}
                      </p>
                    )}
                    <p className="text-xs text-muted mt-1">
                      {new Date(item.submitted_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span className={`rounded-lg border px-2 py-1 text-xs font-medium shrink-0 ${STATUS_BADGE[item.status]}`}>
                    {STATUS_LABEL[item.status]}
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
