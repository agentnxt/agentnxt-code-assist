const messages = document.querySelector("#messages");
const chatForm = document.querySelector("#chat-form");
const settingsForm = document.querySelector("#settings-form");
const instructionInput = document.querySelector("#instruction");
const sendButton = document.querySelector("#send-button");
const clearButton = document.querySelector("#clear-chat");
const statusText = document.querySelector("#status-text");
const output = document.querySelector("#run-output");
const changedFiles = document.querySelector("#changed-files");

const fields = {
  provider: document.querySelector("#provider"),
  model: document.querySelector("#model"),
  apiBase: document.querySelector("#api-base"),
  apiKey: document.querySelector("#api-key"),
  envVars: document.querySelector("#env-vars"),
  serverEnv: document.querySelector("#server-env"),
  repoPath: document.querySelector("#repo-path"),
  files: document.querySelector("#files"),
  autoYes: document.querySelector("#auto-yes"),
  dryRun: document.querySelector("#dry-run"),
  autoCommits: document.querySelector("#auto-commits"),
};

const providerModels = {
  openai: "gpt-4o",
  anthropic: "anthropic/claude-3-5-sonnet-20241022",
  "openai-compatible": "openai/gpt-4o",
  custom: "",
};

function addMessage(role, text, error = false) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "You" : "AX";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (error) {
    bubble.classList.add("is-error");
  }
  bubble.textContent = text;

  article.append(avatar, bubble);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

function filesFromInput(value) {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function envVarsFromInput(value) {
  const env = {};
  for (const rawLine of value.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }
    const separator = line.indexOf("=");
    if (separator < 1) {
      throw new Error(`Invalid environment variable: ${line}`);
    }
    const key = line.slice(0, separator).trim();
    const envValue = line.slice(separator + 1);
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
      throw new Error(`Invalid environment variable name: ${key}`);
    }
    env[key] = envValue;
  }
  return env;
}

function updateChangedFiles(files) {
  changedFiles.replaceChildren();
  if (!files.length) {
    const item = document.createElement("li");
    item.textContent = "No changes reported";
    changedFiles.append(item);
    return;
  }

  for (const file of files) {
    const item = document.createElement("li");
    item.textContent = file;
    changedFiles.append(item);
  }
}

function buildRequest(instruction) {
  return {
    instruction,
    repo_path: fields.repoPath.value.trim(),
    files: filesFromInput(fields.files.value),
    provider: fields.provider.value,
    model: fields.model.value.trim() || null,
    api_base: fields.apiBase.value.trim() || null,
    api_key: fields.apiKey.value.trim() || null,
    env_vars: envVarsFromInput(fields.envVars.value),
    auto_yes: fields.autoYes.checked,
    auto_commits: fields.autoCommits.checked,
    dry_run: fields.dryRun.checked,
    stream: false,
  };
}

async function loadDefaults() {
  const response = await fetch("/config");
  if (!response.ok) {
    return;
  }
  const config = await response.json();
  fields.model.value = config.model || "gpt-4o";
  fields.autoYes.checked = Boolean(config.auto_yes);
  fields.autoCommits.checked = Boolean(config.auto_commits);
  fields.dryRun.checked = Boolean(config.dry_run);
  renderServerEnv(config.env || {});
}

function renderServerEnv(env) {
  fields.serverEnv.replaceChildren();
  const entries = Object.entries(env);
  if (!entries.length) {
    return;
  }

  for (const [key, isSet] of entries) {
    const badge = document.createElement("span");
    badge.className = isSet ? "env-badge is-set" : "env-badge";
    badge.textContent = `${key}: ${isSet ? "set" : "empty"}`;
    fields.serverEnv.append(badge);
  }
}

fields.provider.addEventListener("change", () => {
  const value = providerModels[fields.provider.value];
  if (value !== undefined && !fields.model.value.trim()) {
    fields.model.value = value;
  }
});

clearButton.addEventListener("click", () => {
  messages.replaceChildren();
  addMessage("assistant", "Chat cleared.");
  output.textContent = "No output yet.";
  updateChangedFiles([]);
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const instruction = instructionInput.value.trim();
  if (!instruction || !settingsForm.reportValidity()) {
    return;
  }

  addMessage("user", instruction);
  instructionInput.value = "";
  sendButton.disabled = true;
  statusText.textContent = "Running Aider...";

  let request;
  try {
    request = buildRequest(instruction);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    addMessage("assistant", message, true);
    statusText.textContent = "Failed";
    sendButton.disabled = false;
    return;
  }

  try {
    const response = await fetch("/assist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    const payload = await response.json();
    const result = response.ok ? payload : payload.detail || payload;

    updateChangedFiles(result.changed_files || []);
    output.textContent = result.output || result.error || "No output returned.";

    if (!response.ok || result.error) {
      addMessage("assistant", result.error || "The code assist run failed.", true);
      statusText.textContent = "Failed";
      return;
    }

    const changed = (result.changed_files || []).length;
    addMessage("assistant", `Done. ${changed} changed file${changed === 1 ? "" : "s"} reported.`);
    statusText.textContent = "Ready";
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    addMessage("assistant", message, true);
    output.textContent = message;
    statusText.textContent = "Failed";
  } finally {
    sendButton.disabled = false;
    instructionInput.focus();
  }
});

loadDefaults().catch(() => {
  statusText.textContent = "Ready";
});
