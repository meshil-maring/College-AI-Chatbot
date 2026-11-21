import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../auth/session/AuthProvider.tsx';
import {
  listMyTransferRequests,
  getMyTransferRequest,
  createTransferRequest,
  listSubjectEquivalencies,
  getInstitutionTransferSettings,
} from '../../../services/students/transferApi.ts';
import type {
  TransferRequestList,
  TransferRequestResponse,
  TransferRequestCreate,
  TransferReview,
  TransferComplete,
  TransferEquivalencyList,
  InstitutionTransferSettings,
} from '../../../types/transfer.ts';

/** Query keys for transfer requests. */
export const transferKeys = {
  all: ['student', 'transfer-requests'] as const,
  list: (accessToken: string) => [...transferKeys.all, 'list', accessToken] as const,
  detail: (accessToken: string, requestId: string) =>
    [...transferKeys.all, 'detail', accessToken, requestId] as const,
  equivalencies: (accessToken: string) =>
    [...transferKeys.all, 'equivalencies', accessToken] as const,
  settings: (accessToken: string) => [...transferKeys.all, 'settings', accessToken] as const,
};

/** Load the authenticated student's transfer requests. */
export function useMyTransferRequests(accessToken: string) {
  return useQuery<TransferRequestList, Error>({
    queryKey: transferKeys.list(accessToken),
    queryFn: () => listMyTransferRequests(accessToken),
    enabled: accessToken !== null,
    retry: false,
  });
}

/** Load one transfer request with its action history. */
export function useMyTransferRequest(accessToken: string, requestId: string) {
  return useQuery<TransferRequestResponse, Error>({
    queryKey: transferKeys.detail(accessToken, requestId),
    queryFn: () => getMyTransferRequest(accessToken, requestId),
    enabled: accessToken !== null && requestId !== '',
    retry: false,
  });
}

/** Load subject equivalencies for academic eligibility context. */
export function useSubjectEquivalencies(accessToken: string) {
  return useQuery<TransferEquivalencyList, Error>({
    queryKey: transferKeys.equivalencies(accessToken),
    queryFn: () => listSubjectEquivalencies(accessToken),
    enabled: accessToken !== null,
    retry: false,
  });
}

/** Load institution transfer settings. */
export function useInstitutionTransferSettings(accessToken: string) {
  return useQuery<InstitutionTransferSettings, Error>({
    queryKey: transferKeys.settings(accessToken),
    queryFn: () => getInstitutionTransferSettings(accessToken),
    enabled: accessToken !== null,
    retry: false,
  });
}

/** Submit a new transfer request. Invalidates the request list on success. */
export function useCreateTransferRequest() {
  const queryClient = useQueryClient();
  const { accessToken } = useAuth();
  return useMutation<TransferRequestResponse, Error, TransferRequestCreate>({
    mutationFn: (payload) => createTransferRequest(accessToken as string, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: transferKeys.all });
    },
  });
}