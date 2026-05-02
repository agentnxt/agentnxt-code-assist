'use client';

import { FormEvent, useMemo, useState } from 'react';
import { runAssist } from '../lib/api';
import type { AssistResult } from '../lib/types';

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

const FORBIDDEN_ENV_KEYS = ['OPENAI_API_KEY', 'GITHUB_TOKEN', 'AWS_SECRET_ACCESS_KEY', 'DATABASE_URL'];

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
    if (FORBIDDEN_ENV_KEYS.includes(key)) throw new Error(`Restricted secret key override denied: ${key}`);
    env[key] = line.slice(index + 1);
  }
  return env;
}

function assertSafeBranch(branch: string, label: string): string {
  const value = branch.trim();
  if (!value) return value;
  if (!/^[A-Za-z0-9._\/-]{2,120}$/.test(value)) {
    throw new Error(`${label} contains unsupported characters.`);
  }
  if (value.includes('..') || value.startsWith('/') || value.endsWith('/')) {
    throw new Error(`${label} failed validation.`);
  }
  return value;
}

function assertSafeFiles(files: string[]): string[] {
  return files.map((file) => {
    if (!/^[A-Za-z0-9._\/-]{1,200}$/.test(file)) throw new Error(`Unsafe file path: ${file}`);
    if (file.includes('..') || file.startsWith('/')) throw new Error(`Path traversal denied: ${file}`);
    return file;
  });
}

export default function HomePage() {
  const [instruction, setInstruction] = useState('');
  const [tenantId, setTenantId] = useState('acme-prod');
  const [targetUrl, setTargetUrl] = useState('https://github.com/AGenNext/Platform/issues/1');
  const [repoPath, setRepoPath] = useState('');
  const [workBranch, setWorkBranch] = useState('code-assist/issue-1-phase-1');
  const [files, setFiles] = useState('src/app/layout.tsx\nsrc/app/page.tsx');
  const [checks, setChecks] = useState<string[]>(['production']);
  const [envVars, setEnvVars] = useState('');
  const [model, setModel] = useState('gpt-4o');
  const [dryRun, setDryRun] = useState(false);
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
      const parsedFiles = assertSafeFiles(splitLines(files));
      const branch = assertSafeBranch(workBranch, 'Work branch');
      const tenant = tenantId.trim();
      if (!/^[a-z0-9][a-z0-9-]{1,40}$/.test(tenant)) {
        throw new Error('Tenant ID must be kebab-case and 2-41 chars.');
      }

      const request = {
        instruction: `[tenant:${tenant}] ${instruction}`,
        target_url: targetUrl.trim() || undefined,
        repo_path: targetUrl.trim() ? undefined : repoPath.trim() || undefined,
        work_branch: branch || undefined,
        files: parsedFiles,
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
          <h1>Enterprise-grade Next.js operator console for multi-tenant SaaS workflows.</h1>
          <p>
            Hardened defaults: tenant scoping, strict branch and path validation, and restricted secret
            overrides. Commit, push, and PR actions still require explicit authorization.
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
            Tenant ID
            <input
              value={tenantId}
              onChange={(event) => setTenantId(event.target.value)}
              placeholder="acme-prod"
              required
            />
          </label>

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
            <input value={model} onChange={(event) => setModel(event.target.value)} />
          </label>

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
