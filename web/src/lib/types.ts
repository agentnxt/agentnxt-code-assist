export type CheckResult = {
  command: string;
  exit_code: number;
  stdout_tail?: string;
  stderr_tail?: string;
};

export type RepoAnomaly = {
  severity: 'info' | 'warning' | 'error' | string;
  code: string;
  message: string;
  evidence?: string | null;
};

export type AssistRequest = {
  instruction: string;
  repo_path?: string;
  repo_url?: string;
  repo_full_name?: string;
  target_url?: string;
  base_branch?: string;
  work_branch?: string;
  files: string[];
  checks: string[];
  hydrate_context?: boolean;
  audit_repo?: boolean;
  audit_dependencies?: boolean;
  check_upstream_versions?: boolean;
  fail_on_anomaly_severity?: 'info' | 'warning' | 'error' | null;
  write_change_log?: boolean;
  change_log_path?: string;
  notify_slack?: boolean;
  allow_commits?: boolean;
  allow_push?: boolean;
  allow_pr?: boolean;
  push?: boolean;
  open_pr?: boolean;
  provider?: string;
  model?: string | null;
  api_base?: string | null;
  api_key?: string | null;
  env_vars?: Record<string, string>;
  auto_yes?: boolean;
  auto_commits?: boolean;
  dry_run?: boolean;
};

export type AssistResult = {
  ok: boolean;
  repo_path: string;
  files: string[];
  changed_files: string[];
  output?: string;
  error?: string | null;
  base_branch?: string | null;
  work_branch?: string | null;
  before_sha?: string | null;
  after_sha?: string | null;
  checks: CheckResult[];
  pushed: boolean;
  target_url?: string | null;
  target_kind?: string | null;
  repo_full_name?: string | null;
  hydrated_context?: string | null;
  anomalies: RepoAnomaly[];
  change_log?: string | null;
  change_log_path?: string | null;
  slack?: { sent: boolean; error?: string | null };
};
