import { notifySessionExpired } from '../shared/sessionEvents.ts';
import type {
  TransferComplete,
  TransferRequestCreate,
  TransferRequestList,
  TransferRequestListItem,
  TransferRequestResponse,
  TransferReview,
  TransferEquivalency,
  TransferEquivalencyList,
  InstitutionTransferSettings,
  InstitutionTransferSettingsUpdate,
  TransferEquivalencyCreate,
} from '../../types/transfer.ts';

const BASE = `${(import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')}/v1/transfer-requests`;

export class TransferApiError extends Error {
  readonly status: number;
  readonly details: unknown;
  readonly code: string | null;
  constructor(status: number, message: string, details?: unknown, code: string | null = null) {
    super(message);
    this.name = 'TransferApiError';
    this.status = status;
    this.details = details;
    this.code = code;
  }
}

async function getJson<T>(endpoint: string, accessToken: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(endpoint, { method: 'GET', headers: { Authorization: `Bearer ${accessToken}` } });
  } catch {
    throw new TransferApiError(
      0,
      'Could not reach the backend. Please make sure the server is running.',
      undefined,
      'NETWORK_ERROR',
    );
  }
  if (!response.ok) {
    let details: unknown;
    if (response.headers.get('content-type')?.includes('application/json')) {
      try {
        details = await response.json();
      } catch {
        details = undefined;
      }
    }
    let message = `Request failed with HTTP ${response.status}`;
    let code: string | null = null;
    if (typeof details === 'object' && details !== null) {
      const body = details as Record<string, unknown>;
      if (typeof body.detail === 'string' && body.detail) message = body.detail;
      if (typeof body.error === 'object' && body.error !== null) {
        const error = body.error as Record<string, unknown>;
        if (typeof error.code === 'string') code = error.code;
        if (typeof error.message === 'string' && error.message) message = error.message;
        else if (code && message.startsWith('Request failed with HTTP')) message = `Request failed (${code})`;
      }
    }
    if (response.status === 401) notifySessionExpired(accessToken);
    throw new TransferApiError(response.status, message, details, code);
  }
  return (await response.json()) as T;
}

async function postJson<T>(endpoint: string, accessToken: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new TransferApiError(0, 'Could not reach the backend.', undefined, 'NETWORK_ERROR');
  }
  if (!response.ok) {
    let details: unknown;
    if (response.headers.get('content-type')?.includes('application/json')) {
      try { details = await response.json(); } catch { details = undefined; }
    }
    let message = `Request failed with HTTP ${response.status}`;
    let code: string | null = null;
    if (typeof details === 'object' && details !== null) {
      const body = details as Record<string, unknown>;
      if (typeof body.detail === 'string' && body.detail) message = body.detail;
      if (typeof body.error === 'object' && body.error !== null) {
        const error = body.error as Record<string, unknown>;
        if (typeof error.code === 'string') code = error.code;
        if (typeof error.message === 'string' && error.message) message = error.message;
        else if (code && message.startsWith('Request failed with HTTP')) message = `Request failed (${code})`;
      }
    }
    if (response.status === 401) notifySessionExpired(accessToken);
    throw new TransferApiError(response.status, message, details, code);
  }
  return (await response.json()) as T;
}

async function putJson<T>(endpoint: string, accessToken: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new TransferApiError(0, 'Could not reach the backend.', undefined, 'NETWORK_ERROR');
  }
  if (!response.ok) {
    let details: unknown;
    if (response.headers.get('content-type')?.includes('application/json')) {
      try { details = await response.json(); } catch { details = undefined; }
    }
    let message = `Request failed with HTTP ${response.status}`;
    let code: string | null = null;
    if (typeof details === 'object' && details !== null) {
      const body = details as Record<string, unknown>;
      if (typeof body.detail === 'string' && body.detail) message = body.detail;
      if (typeof body.error === 'object' && body.error !== null) {
        const error = body.error as Record<string, unknown>;
        if (typeof error.code === 'string') code = error.code;
        if (typeof error.message === 'string' && error.message) message = error.message;
        else if (code && message.startsWith('Request failed with HTTP')) message = `Request failed (${code})`;
      }
    }
    if (response.status === 401) notifySessionExpired(accessToken);
    throw new TransferApiError(response.status, message, details, code);
  }
  return (await response.json()) as T;
}
/** List the authenticated student's transfer requests. */
export function listMyTransferRequests(
  accessToken: string,
): Promise<TransferRequestList> {
  return getJson(`${BASE}`, accessToken);
}

/** Get one transfer request with eligibility and approval history. */
export function getMyTransferRequest(
  accessToken: string,
  requestId: string,
): Promise<TransferRequestResponse> {
  return getJson(`${BASE}/${encodeURIComponent(requestId)}`, accessToken);
}

/** Submit a new transfer request. */
export function createTransferRequest(
  accessToken: string,
  payload: TransferRequestCreate,
): Promise<TransferRequestResponse> {
  return postJson(`${BASE}`, accessToken, payload);
}

/** List subject equivalencies for academic eligibility context. */
export function listSubjectEquivalencies(
  accessToken: string,
): Promise<TransferEquivalencyList> {
  return getJson(`${BASE}/equivalencies`, accessToken);
}

/** Get institution transfer settings. */
export function getInstitutionTransferSettings(
  accessToken: string,
): Promise<InstitutionTransferSettings> {
  return getJson(`${BASE}/settings`, accessToken);
}