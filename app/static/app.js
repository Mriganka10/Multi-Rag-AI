const authScreen = document.querySelector("#authScreen");
const workspace = document.querySelector("#workspace");
const otpRequestForm = document.querySelector("#otpRequestForm");
const otpVerifyForm = document.querySelector("#otpVerifyForm");
const emailInput = document.querySelector("#emailInput");
const otpInput = document.querySelector("#otpInput");
const changeEmailButton = document.querySelector("#changeEmailButton");
const authStatus = document.querySelector("#authStatus");
const userEmail = document.querySelector("#userEmail");
const signOutButton = document.querySelector("#signOutButton");

const form = document.querySelector("#analysisForm");
const promptInput = document.querySelector("#promptInput");
const fileInput = document.querySelector("#fileInput");
const attachButton = document.querySelector("#attachButton");
const removeFileButton = document.querySelector("#removeFile");
const attachmentBar = document.querySelector("#attachmentBar");
const attachmentName = document.querySelector("#attachmentName");
const submitButton = document.querySelector("#submitButton");
const conversation = document.querySelector("#conversation");
const learningConsent = document.querySelector("#learningConsent");
const approveLearning = document.querySelector("#approveLearning");
const healthStatus = document.querySelector("#healthStatus");

let pendingEmail = "";

function setHealth(status, text) {
  healthStatus.className = `status-pill ${status}`;
  healthStatus.textContent = text;
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error("Health check failed");
    }
    setHealth("ok", "API online");
  } catch {
    setHealth("error", "API offline");
  }
}

function setAuthStatus(text, state = "") {
  authStatus.textContent = text;
  authStatus.className = `auth-status ${state}`.trim();
}

function renderFreshWorkspace(user) {
  userEmail.textContent = user.email;
  authScreen.hidden = true;
  workspace.hidden = false;
  promptInput.value = "";
  fileInput.value = "";
  learningConsent.checked = false;
  approveLearning.checked = false;
  updateAttachment();
  conversation.replaceChildren();
  addMessage(
    "assistant",
    "Welcome. Upload a notice, bank statement, financial report, ITR file, or write a prompt below. This workspace is fresh for your signed-in email.",
  );
  checkHealth();
}

function showSignIn() {
  workspace.hidden = true;
  authScreen.hidden = false;
  otpRequestForm.hidden = false;
  otpVerifyForm.hidden = true;
  otpInput.value = "";
  setAuthStatus("");
  emailInput.focus();
}

async function loadSession() {
  try {
    const response = await fetch("/api/v1/auth/me");
    if (!response.ok) {
      showSignIn();
      return;
    }
    const user = await response.json();
    renderFreshWorkspace(user);
  } catch {
    showSignIn();
  }
}

async function requestOtp(event) {
  event.preventDefault();
  const email = emailInput.value.trim().toLowerCase();
  if (!email) {
    emailInput.focus();
    return;
  }

  setAuthStatus("Sending OTP...", "info");
  const response = await fetch("/api/v1/auth/request-otp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    setAuthStatus(payload.detail || "Unable to send OTP.", "error");
    return;
  }

  pendingEmail = email;
  otpRequestForm.hidden = true;
  otpVerifyForm.hidden = false;
  otpInput.focus();
  const devOtp = payload.dev_otp ? ` Development OTP: ${payload.dev_otp}` : "";
  setAuthStatus(`OTP sent to ${email}.${devOtp}`, "success");
}

async function verifyOtp(event) {
  event.preventDefault();
  const otp = otpInput.value.trim();
  if (!pendingEmail || !otp) {
    otpInput.focus();
    return;
  }

  setAuthStatus("Verifying OTP...", "info");
  const response = await fetch("/api/v1/auth/verify-otp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: pendingEmail, otp }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    setAuthStatus(payload.detail || "Invalid OTP.", "error");
    return;
  }

  renderFreshWorkspace(payload);
}

async function signOut() {
  await fetch("/api/v1/auth/logout", { method: "POST" }).catch(() => {});
  pendingEmail = "";
  showSignIn();
}

function addMessage(role, text, meta = [], agent = "") {
  const article = document.createElement("article");
  article.className = `message ${role === "user" ? "user-message" : "assistant-message"}`;

  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "You" : "Assistant";

  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = text;

  article.append(label);

  if (role !== "user" && agent) {
    const agentBanner = document.createElement("div");
    agentBanner.className = "agent-banner";
    agentBanner.textContent = `Selected agent: ${agent}`;
    article.append(agentBanner);
  }

  article.append(body);

  if (meta.length > 0) {
    const metaRow = document.createElement("div");
    metaRow.className = "message-meta";
    for (const item of meta) {
      const chip = document.createElement("span");
      chip.textContent = item;
      metaRow.append(chip);
    }
    article.append(metaRow);
  }

  conversation.append(article);
  window.requestAnimationFrame(() => {
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: "smooth",
    });
  });
}

function getSelectedFile() {
  return fileInput.files && fileInput.files.length > 0 ? fileInput.files[0] : null;
}

function updateAttachment() {
  const file = getSelectedFile();
  if (!file) {
    attachmentName.textContent = "";
    attachmentBar.hidden = true;
    return;
  }

  const sizeKb = Math.max(1, Math.round(file.size / 1024));
  attachmentName.textContent = `${file.name} (${sizeKb} KB)`;
  attachmentBar.hidden = false;
}

function buildUserPreview(prompt, file) {
  if (!file) {
    return prompt;
  }
  return `${prompt}\n\nAttached file: ${file.name}`;
}

async function analyzeText(prompt) {
  return fetch("/api/v1/tasks/analyze-text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: prompt,
      text: prompt,
      learning_consent: learningConsent.checked,
      approve_learning: approveLearning.checked,
    }),
  });
}

async function analyzeFile(prompt, file) {
  const formData = new FormData();
  formData.append("query", prompt);
  formData.append("file", file);
  formData.append("learning_consent", String(learningConsent.checked));
  formData.append("approve_learning", String(approveLearning.checked));

  return fetch("/api/v1/tasks/analyze-file", {
    method: "POST",
    body: formData,
  });
}

function responseMeta(response) {
  const agent = response.headers.get("x-agent-selected");
  const provider = response.headers.get("x-llm-provider");
  const model = response.headers.get("x-llm-model");
  const fallback = response.headers.get("x-llm-fallback");
  const meta = [];

  if (agent) {
    meta.push(`Agent: ${agent}`);
  }
  if (provider) {
    meta.push(`Provider: ${provider}`);
  }
  if (model) {
    meta.push(`Model: ${model}`);
  }
  if (fallback) {
    meta.push(`Fallback: ${fallback}`);
  }

  return meta;
}

function responseAgent(response) {
  return response.headers.get("x-agent-selected") || "";
}

async function handleSubmit(event) {
  event.preventDefault();

  const prompt = promptInput.value.trim();
  const file = getSelectedFile();

  if (!prompt) {
    promptInput.focus();
    return;
  }

  addMessage("user", buildUserPreview(prompt, file));
  promptInput.value = "";
  fileInput.value = "";
  updateAttachment();
  submitButton.disabled = true;
  submitButton.textContent = "Analyzing...";

  try {
    const response = file ? await analyzeFile(prompt, file) : await analyzeText(prompt);
    const text = await response.text();
    const meta = responseMeta(response);
    const agent = responseAgent(response);

    if (response.status === 401) {
      showSignIn();
      return;
    }
    if (!response.ok) {
      addMessage("assistant", text || `Request failed with status ${response.status}`, meta, agent);
      return;
    }

    addMessage("assistant", text, meta, agent);
  } catch (error) {
    addMessage(
      "assistant",
      `Unable to reach the analysis API. ${error instanceof Error ? error.message : ""}`.trim(),
    );
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Analyze";
  }
}

otpRequestForm.addEventListener("submit", requestOtp);
otpVerifyForm.addEventListener("submit", verifyOtp);
changeEmailButton.addEventListener("click", () => {
  pendingEmail = "";
  otpVerifyForm.hidden = true;
  otpRequestForm.hidden = false;
  otpInput.value = "";
  setAuthStatus("");
  emailInput.focus();
});
signOutButton.addEventListener("click", signOut);
attachButton.addEventListener("click", () => fileInput.click());
removeFileButton.addEventListener("click", () => {
  fileInput.value = "";
  updateAttachment();
});
fileInput.addEventListener("change", updateAttachment);
form.addEventListener("submit", handleSubmit);

promptInput.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    form.requestSubmit();
  }
});

loadSession();
