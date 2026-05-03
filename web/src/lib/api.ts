import type { AssistRequest, AssistResult, AuthResponse, ProviderSetup } from './types';

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

// === Auth/Provider API ===

export async function listProviders(): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/auth/providers`);
  return response.json();
}

export async function getProvider(provider: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/auth/providers/${provider}`);
  return response.json();
}

export async function loginWithProvider(provider: string): Promise<{redirect: string}> {
  const response = await fetch(`${API_BASE}/auth/login/${provider}`);
  return response.json();
}

export async function setupProvider(
  provider: string,
  setup: ProviderSetup
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/auth/providers/${provider}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(setup),
  });
  return response.json();
}

export async function removeProvider(provider: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/auth/providers/${provider}`, {
    method: 'DELETE',
  });
  return response.json();
}
