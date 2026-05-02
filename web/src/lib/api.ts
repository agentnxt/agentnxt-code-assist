import type { AssistRequest, AssistResult } from './types';

export const API_BASE =
  process.env.NEXT_PUBLIC_AGENNEXT_CODE_ASSIST_API_URL || 'http://localhost:8090';

export async function runAssist(request: AssistRequest): Promise<AssistResult> {
  const response = await fetch(`${API_BASE}/assist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  const payload = await response.json();
  if (!response.ok) {
    const detail = payload?.detail ?? payload;
    const message = detail?.error || payload?.error || response.statusText;
    throw Object.assign(new Error(message), { payload: detail });
  }
  return payload as AssistResult;
}

export async function getHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/healthz`, { cache: 'no-store' });
    return response.ok;
  } catch {
    return false;
  }
}
