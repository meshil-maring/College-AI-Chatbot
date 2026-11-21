import { useState } from 'react';
import { Target, BookOpen } from 'lucide-react';
import type { TransferRequestCreate, TransferRequestResponse, TransferType, AcademicPlacement } from '../../../types/transfer.ts';
import { createTransferRequest } from '../../../services/students/transferApi.ts';
import { useAuth } from '../../auth/session/AuthProvider.tsx';
import { useApiMutation } from '../../../hooks/useApiQuery.ts';
import { queryClient } from '../../../lib/queryClient.ts';

interface TransferFormProps {
  currentPlacement: AcademicPlacement | null;
  targetPrograms: { id: string; name: string }[];
  targetSemesters: { id: string; name: string }[];
  targetSections: { id: string; name: string }[];
  onSuccess?: (requestId: string) => void;
}

export default function TransferForm({ currentPlacement, targetPrograms, targetSemesters, targetSections, onSuccess }: TransferFormProps) {
  const { accessToken } = useAuth();
  const [transferType, setTransferType] = useState<TransferType>('section_transfer');
  const [targetProgramId, setTargetProgramId] = useState<string>('');
  const [targetSectionId, setTargetSectionId] = useState<string>('');
  const [targetSemesterId, setTargetSemesterId] = useState<string>('');
  const [reason, setReason] = useState('');
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const mutation = useApiMutation<TransferRequestResponse, TransferRequestCreate>({
    mutationFn: (payload) => createTransferRequest(accessToken as string, payload),
    onSuccess: (data) => {
      setSubmitting(false);
      setSuccessMessage(`Transfer request submitted: ${data.request.request_id}`);
      if (onSuccess) onSuccess(data.request.request_id);
      void queryClient.invalidateQueries({ queryKey: ['student', 'transfer-requests'] });
    },
    onError: (error) => {
      setSubmitting(false);
      setSubmitError(error instanceof Error ? error.message : 'Transfer request failed.');
    },
  });

  const isSectionTransfer = transferType === 'section_transfer';
  const isProgramTransfer = transferType === 'program_transfer';
  const canSubmit = reason.trim().length > 0 && acknowledged && !submitting && (isSectionTransfer ? targetSectionId !== '' : targetProgramId !== '');

  const confirmSubmit = () => {
    setSubmitError(null);
    setSubmitting(true);
    void mutation.mutate({
      student_id: '', transfer_type: transferType,
      target_program_id: isProgramTransfer && targetProgramId ? targetProgramId : currentPlacement?.program_id ?? '',
      target_batch_id: null,
      target_section_id: isSectionTransfer && targetSectionId ? targetSectionId : currentPlacement?.section_id ?? '',
      target_semester_id: isProgramTransfer && targetSemesterId ? targetSemesterId : currentPlacement?.semester_id ?? '',
      target_curriculum_version_id: null, reason: reason.trim(), supporting_documents: [], effective_date: null,
    });
  };

  return (
    <form onSubmit={(e) => { e.preventDefault(); if (canSubmit) confirmSubmit(); }} className="space-y-5">
      <div className="rounded-xl border border-line bg-surface p-4 sm:p-5">
        <h3 className="font-semibold text-content text-section">Transfer Details</h3>
        <div className="mt-5">
          <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-2">1. Transfer Type</label>
          <div className="grid grid-cols-1 gap-3">
            <button key="section_transfer" type="button" onClick={() => setTransferType('section_transfer')} className={`flex items-start gap-3 p-3 rounded-lg border-2 text-left transition-all ${transferType === 'section_transfer' ? 'border-accent bg-accent/10' : 'border-line hover:border-control-hover hover:bg-surface-hover'}`}>
              <Target size={20} aria-hidden="true" className="flex-shrink-0 mt-0.5" />
              <div className="min-w-0"><span className="block font-medium text-content">Section Transfer</span><span className="block text-xs text-muted">Move to a different section within the same program.</span></div>
            </button>
            <button key="program_transfer" type="button" onClick={() => setTransferType('program_transfer')} className={`flex items-start gap-3 p-3 rounded-lg border-2 text-left transition-all ${transferType === 'program_transfer' ? 'border-accent bg-accent/10' : 'border-line hover:border-control-hover hover:bg-surface-hover'}`}>
              <BookOpen size={20} aria-hidden="true" className="flex-shrink-0 mt-0.5" />
              <div className="min-w-0"><span className="block font-medium text-content">Program Transfer</span><span className="block text-xs text-muted">Switch to a different academic program or department.</span></div>
            </button>
          </div>
        </div>