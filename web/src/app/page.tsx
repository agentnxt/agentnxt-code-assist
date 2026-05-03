'use client';

import { FormEvent, useMemo, useState, useEffect } from 'react';
import { runAssist, listProviders, getProvider, loginWithProvider, listLocalModels } from '../lib/api';
import type { AssistResult, AuthResponse } from '../lib/types';

const CHECK_PRESETS = [
  'production',
  'dependency',
  'typecheck',
  'lint',
  'unit',
  'integration',
  'smoke',
  'docker',
  'docker-smoke',
  'publishable',
];

function splitLines(value: string): string[] {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseEnvVars(value: string): Record<string, string> {
  const env: Record<string, string> = {};
  for (const raw of value.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const index = line.indexOf('=');
    if (index < 1) throw new Error(`Invalid env var: ${line}`);
    const key = line.slice(0, index).trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) throw new Error(`Invalid env var name: ${key}`);
    env[key] = line.slice(index + 1);
  }
  return env;
}

export default function HomePage() {
  const [instruction, setInstruction] = useState('');
  const [targetUrl, setTargetUrl] = useState('https://github.com/AGenNext/Platform/issues/1');
  const [repoPath, setRepoPath] = useState('');
  const [workBranch, setWorkBranch] = useState('code-assist/issue-1-phase-1');
  const [files, setFiles] = useState('src/app/layout.tsx\nsrc/app/page.tsx');
  const [checks, setChecks] = useState<string[]>(['production']);
  const [envVars, setEnvVars] = useState('');
  const [model, setModel] = useState('gpt-4o');
  const [provider, setProvider] = useState('openai');
  const [providerModels, setProviderModels] = useState<string[]>([]);
  const [providerApiBase, setProviderApiBase] = useState('');
  const [dryRun, setDryRun] = useState(false);
  const [localModelInstalled, setLocalModelInstalled] = useState(false);
  const [isAirGapped, setIsAirGapped] = useState(false);
  const [modelInfo, setModelInfo] = useState<{installed: string[], available: Record<string, string>, air_gapped: boolean}>({installed: [], available: {}, air_gapped: false});
  const [notifySlack, setNotifySlack] = useState(false);
  const [checkUpstream, setCheckUpstream] = useState(false);
  const [allowCommits, setAllowCommits] = useState(false);
  const [allowPush, setAllowPush] = useState(false);
  const [allowPr, setAllowPr] = useState(false);
  const [push, setPush] = useState(false);
  const [openPr, setOpenPr] = useState(false);
  const [result, setResult] = useState<AssistResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [authMessage, setAuthMessage] = useState<string | null>(null);

  // Load available providers on mount
  useEffect(() => {
    loadProviders();
  }, []);

  async function loadProviders() {
    try {
      const res = await listProviders();
      setProviderModels(['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo']);
      
      // Check for local models
      try {
        const localInfo = await listLocalModels();
        setModelInfo(localInfo);
        setIsAirGapped(localInfo.air_gapped);
        setLocalModelInstalled(localInfo.installed.length > 0 || Object.keys(localInfo.available).length > 0);
      } catch {
        // Local models not available
      }
    } catch (e) {
      console.error('Failed to load providers:', e);
    }
  }

  const selectedChecks = useMemo(() => checks.join(', '), [checks]);

  function toggleCheck(check: string) {
    setChecks((current) =>
      current.includes(check) ? current.filter((item) => item !== check) : [...current, check],
    );
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const request = {
        instruction,
        target_url: targetUrl.trim() || undefined,
        repo_path: targetUrl.trim() ? undefined : repoPath.trim() || undefined,
        work_branch: workBranch.trim() || undefined,
        files: splitLines(files),
        checks,
        model: model.trim() || null,
        env_vars: parseEnvVars(envVars),
        dry_run: dryRun,
        notify_slack: notifySlack,
        check_upstream_versions: checkUpstream,
        allow_commits: allowCommits,
        allow_push: allowPush,
        allow_pr: allowPr,
        push,
        open_pr: openPr,
        auto_commits: allowCommits,
        write_change_log: true,
        audit_repo: true,
        audit_dependencies: true,
        hydrate_context: true,
      };
      const response = await runAssist(request);
      setResult(response);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : String(caught);
      const payload = (caught as { payload?: AssistResult })?.payload;
      setError(message);
      if (payload) setResult(payload);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">AGenNext Code Assist</p>
          <h1>Chat with a repo, run production checks, and review before pushing.</h1>
          <p>
            Optional Next.js operator UI for the FastAPI backend. Safety defaults stay enforced: no commit,
            push, PR, or merge unless explicitly authorized.
          </p>
        </div>
        <div className="status-card">
          <span>Backend</span>
          <strong>{process.env.NEXT_PUBLIC_AGENNEXT_CODE_ASSIST_API_URL || 'http://localhost:8090'}</strong>
        </div>
      </section>

      <form className="grid" onSubmit={onSubmit}>
        <section className="panel main-panel">
          <label>
            Instruction
            <textarea
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
              placeholder="Phase 1 only: fix app shell/build issues. Keep the change focused."
              rows={7}
              required
            />
          </label>

          <label>
            Target URL
            <input
              value={targetUrl}
              onChange={(event) => setTargetUrl(event.target.value)}
              placeholder="https://github.com/AGenNext/Platform/issues/1"
            />
          </label>

          <label>
            Local repo path fallback
            <input
              value={repoPath}
              onChange={(event) => setRepoPath(event.target.value)}
              placeholder="/srv/agennext/repos/Platform"
              disabled={Boolean(targetUrl.trim())}
            />
          </label>

          <label>
            Work branch
            <input value={workBranch} onChange={(event) => setWorkBranch(event.target.value)} />
          </label>

          <label>
            Files
            <textarea value={files} onChange={(event) => setFiles(event.target.value)} rows={5} />
          </label>
        </section>

        <aside className="panel side-panel">
          <h2>Checks</h2>
          <p className="muted">Selected: {selectedChecks || 'none'}</p>
          <div className="chips">
            {CHECK_PRESETS.map((check) => (
              <button
                key={check}
                type="button"
                className={checks.includes(check) ? 'chip selected' : 'chip'}
                onClick={() => toggleCheck(check)}
              >
                {check}
              </button>
            ))}
          </div>

          <label>
            Model
            <select
              value={model}
              onChange={(event) => setModel(event.target.value)}
            >
              {provider === 'local' ? (
                <>
                  <option value="">Select model</option>
                  <option value="llama3-8b">Llama 3 8B (4.9GB)</option>
                  <option value="mistral-7b">Mistral 7B (4.1GB)</option>
                  <option value="phi3-mini">Phi-3 Mini (2.3GB)</option>
                </>
              ) : provider === 'google' ? (
                <>
                  <option value="">Select model</option>
                  <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                  <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                  <option value="gemini-1.0-pro">Gemini 1.0 Pro</option>
                </>
              ) : (
                <>
                  <option value="">Select provider first</option>
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="gpt-4-turbo">GPT-4 Turbo</option>
                  <option value="gpt-4">GPT-4</option>
                  <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                  <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                  <option value="claude-3-opus-20240229">Claude 3 Opus</option>
                  <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
                </>
              )}
            </select>
          </label>

          <section className="panel settings-panel">
            <h2>Provider Settings</h2>
            <p className="muted">Sign in with your provider account to automatically get an API key, or use a local model when API limits are exhausted</p>
            
            <label>
              Provider
              <select
                value={provider}
                onChange={(event) => {
                  setProvider(event.target.value);
                  setModel('gpt-4o');
                }}
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="google">Google (Gemini)</option>
                <option value="local">Local (llama.cpp)</option>
                <option value="gateway">Custom Gateway</option>
              </select>
            </label>

            {provider === 'local' && (
              <div className="local-options">
                <p className="muted">
                  {isAirGapped ? (
                    <>🔒 Air-gapped mode - only local models available</>
                  ) : (
                    <>Local models run offline using llama.cpp - useful when API limits are exhausted.</>
                  )}
                  {!localModelInstalled && " Install llama.cpp first: "}
                  {localModelInstalled && " Available: "}
                  {localModelInstalled && modelInfo.available.map((m: string) => <span key={m} className="chip">{m}</span>)}
                </p>
                {!localModelInstalled && (
                  <button className="chip" onClick={() => window.open('https://github.com/ggerganov/llama.cpp', '_blank')}>
                    Install llama.cpp
                  </button>
                )}
                {localModelInstalled && modelInfo.installed.length === 0 && (
                  <button className="chip" onClick={() => {
                    // Download first available model
                    const modelToDownload = Object.keys(modelInfo.available)[0];
                    // TODO: trigger download
                  }}>
                    Download {modelToDownload}
                  </button>
                )}
              </div>
            )}

            {provider === 'gateway' && (
              <label>
                API Base URL
                <input
                  value={providerApiBase}
                  onChange={(event) => setProviderApiBase(event.target.value)}
                  placeholder="https://llm.example.com/v1"
                />
              </label>
            )}

            {(provider !== 'gateway' && provider !== 'local') && (
              <button
                className="chip"
                onClick={async () => {
                  try {
                    setLoading(true);
                    const res = await loginWithProvider(provider);
                    // Open provider login in new tab/window
                    window.open(res.redirect, '_blank', 'width=600,height=700');
                    setAuthMessage(`Please sign in with ${provider} in the new window. After signing in, your API key will be auto-created and stored securely for this session. You can also manage your API keys at: ${provider === 'openai' ? 'platform.openai.com/settings' : provider === 'anthropic' ? 'console.anthropic.com/settings' : 'aistudio.google.com/app'}`);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : 'Failed to initiate login');
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading}
              >
                {loading ? 'Loading...' : 'Sign in with ' + provider}
              </button>
            )}

            {authMessage && <p className="muted">{authMessage}</p>}
          </section>

          <label>
            Environment variables
            <textarea
              value={envVars}
              onChange={(event) => setEnvVars(event.target.value)}
              rows={4}
              placeholder="OPENAI_API_BASE=https://llm.example/v1"
            />
          </label>

          <div className="toggles">
            <label><input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} /> Dry run</label>
            <label><input type="checkbox" checked={checkUpstream} onChange={(e) => setCheckUpstream(e.target.checked)} /> Check upstream versions</label>
            <label><input type="checkbox" checked={notifySlack} onChange={(e) => setNotifySlack(e.target.checked)} /> Notify Slack</label>
          </div>

          <h2>Guardrails</h2>
          <div className="toggles warning-box">
            <label><input type="checkbox" checked={allowCommits} onChange={(e) => setAllowCommits(e.target.checked)} /> Allow commits</label>
            <label><input type="checkbox" checked={allowPush} onChange={(e) => setAllowPush(e.target.checked)} /> Allow push</label>
            <label><input type="checkbox" checked={allowPr} onChange={(e) => setAllowPr(e.target.checked)} /> Allow PR</label>
            <label><input type="checkbox" checked={push} onChange={(e) => setPush(e.target.checked)} /> Request push</label>
            <label><input type="checkbox" checked={openPr} onChange={(e) => setOpenPr(e.target.checked)} /> Request PR</label>
          </div>

          <button className="run" disabled={loading} type="submit">
            {loading ? 'Running…' : 'Run Code Assist'}
          </button>
        </aside>
      </form>

      {(error || result) && (
        <section className="results">
          {error && <div className="error">{error}</div>}
          {result && (
            <>
              <div className="result-grid">
                <article className="panel">
                  <h2>Changed files</h2>
                  <ul>
                    {(result.changed_files || []).map((file) => <li key={file}>{file}</li>)}
                    {!result.changed_files?.length && <li>No changes reported</li>}
                  </ul>
                </article>
                <article className="panel">
                  <h2>Checks</h2>
                  <ul>
                    {(result.checks || []).map((check) => (
                      <li key={check.command} className={check.exit_code === 0 ? 'pass' : 'fail'}>
                        {check.command}: exit {check.exit_code}
                      </li>
                    ))}
                    {!result.checks?.length && <li>No checks run</li>}
                  </ul>
                </article>
                <article className="panel">
                  <h2>Anomalies</h2>
                  <ul>
                    {(result.anomalies || []).map((item) => (
                      <li key={`${item.code}-${item.evidence || ''}`}>[{item.severity}] {item.code}: {item.message}</li>
                    ))}
                    {!result.anomalies?.length && <li>No anomalies reported</li>}
                  </ul>
                </article>
              </div>
              <article className="panel log-panel">
                <h2>Change log</h2>
                <pre>{result.change_log || 'No change log returned.'}</pre>
              </article>
              <article className="panel log-panel">
                <h2>Output</h2>
                <pre>{result.output || result.error || 'No output returned.'}</pre>
              </article>
            </>
          )}
        </section>
      )}
    </main>
  );
}
