import type { AdversarialResponse, ScanResponse } from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export class ScanClientError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = 'ScanClientError';
    this.status = status;
  }
}

async function postScan<T>(path: string, file: File): Promise<T> {
  const body = new FormData();
  body.append('file', file);
  let response: Response;
  try {
    // TEMP: client timeout removed for diagnosis, see fix-adversarial-latency-prompt.md.
    response = await fetch(`${API_BASE_URL}${path}`, { method: 'POST', body });
  } catch {
    throw new ScanClientError('The ScanEx backend could not be reached. Start it on port 8000 and try again.');
  }

  if (!response.ok) {
    let detail = `Scan failed with HTTP ${response.status}.`;
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail || detail;
    } catch {
      // Preserve the status-based message when the server did not return JSON.
    }
    if (response.status === 413) detail = 'This file exceeds the backend 25 MB limit.';
    if (response.status === 415) detail = payloadDetail(detail, 'This file type is not supported by the backend.');
    throw new ScanClientError(detail, response.status);
  }

  return (await response.json()) as T;
}

function payloadDetail(detail: string, fallback: string): string {
  return detail || fallback;
}

export function scanBaseline(file: File): Promise<ScanResponse> {
  return postScan<ScanResponse>('/scan/baseline', file);
}

export function scanAdversarial(file: File): Promise<AdversarialResponse> {
  return postScan<AdversarialResponse>('/scan/adversarial', file);
}
