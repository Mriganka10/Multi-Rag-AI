const form = document.querySelector("#analysisForm");
const promptInput = document.querySelector("#promptInput");
const fileInput = document.querySelector("#fileInput");
const attachButton = document.querySelector("#attachButton");
const removeFileButton = document.querySelector("#removeFile");
const attachmentBar = document.querySelector("#attachmentBar");
const attachmentName = document.querySelector("#attachmentName");
const submitButton = document.querySelector("#submitButton");
const conversation = document.querySelector("#conversation");
const tenantId = document.querySelector("#tenantId");
const learningConsent = document.querySelector("#learningConsent");
const approveLearning = document.querySelector("#approveLearning");
const healthStatus = document.querySelector("#healthStatus");

const examples = {
  scn: `Analyze this GST show cause notice and draft a professional reply.

Show Cause Notice under section 73 of the CGST Act.
It is alleged that input tax credit of INR 250000 was wrongly availed due to mismatch between GSTR-2B and GSTR-3B for FY 2024-25.
The taxpayer is required to explain why tax, interest and penalty should not be recovered.`,
  bank: `Analyze this bank statement and highlight cash deposits, interest, EMI, and high-value transactions.

2026-04-03 Cash Deposit 0 150000 400000
2026-04-07 Vendor Payment 85000 0 315000
2026-04-11 Interest Credit 0 3500 318500
2026-04-15 Loan EMI 45000 0 273500
2026-04-20 High Value Receipt 0 250000 523500`,
  financial: `Analyze financial statement ratios and anomalies.

Current Assets 500000
Current Liabilities 250000
Inventory 100000
Total Debt 800000
Equity 300000
Revenue 1200000
Net Profit 180000
Total Assets 1000000
Total Liabilities 650000`,
};

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

function addMessage(role, text, meta = []) {
  const article = document.createElement("article");
  article.className = `message ${role === "user" ? "user-message" : "assistant-message"}`;

  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "You" : "Assistant";

  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = text;

  article.append(label, body);

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
  article.scrollIntoView({ behavior: "smooth", block: "end" });
}

function getSelectedFile() {
  return fileInput.files && fileInput.files.length > 0 ? fileInput.files[0] : null;
}

function updateAttachment() {
  const file = getSelectedFile();
  if (!file) {
    attachmentBar.hidden = true;
    attachmentName.textContent = "";
    return;
  }

  const sizeKb = Math.max(1, Math.round(file.size / 1024));
  attachmentName.textContent = `${file.name} (${sizeKb} KB)`;
  attachmentBar.hidden = false;
}

function normalizeTenant(value) {
  return value.trim() || "default";
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
      tenant_id: normalizeTenant(tenantId.value),
      learning_consent: learningConsent.checked,
      approve_learning: approveLearning.checked,
    }),
  });
}

async function analyzeFile(prompt, file) {
  const formData = new FormData();
  formData.append("query", prompt);
  formData.append("file", file);
  formData.append("tenant_id", normalizeTenant(tenantId.value));
  formData.append("learning_consent", String(learningConsent.checked));
  formData.append("approve_learning", String(approveLearning.checked));

  return fetch("/api/v1/tasks/analyze-file", {
    method: "POST",
    body: formData,
  });
}

function responseMeta(response) {
  const provider = response.headers.get("x-llm-provider");
  const model = response.headers.get("x-llm-model");
  const fallback = response.headers.get("x-llm-fallback");
  const meta = [];

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

async function handleSubmit(event) {
  event.preventDefault();

  const prompt = promptInput.value.trim();
  const file = getSelectedFile();

  if (!prompt) {
    promptInput.focus();
    return;
  }

  addMessage("user", buildUserPreview(prompt, file));
  submitButton.disabled = true;
  submitButton.textContent = "Analyzing...";

  try {
    const response = file ? await analyzeFile(prompt, file) : await analyzeText(prompt);
    const text = await response.text();
    const meta = responseMeta(response);

    if (!response.ok) {
      addMessage("assistant", text || `Request failed with status ${response.status}`, meta);
      return;
    }

    addMessage("assistant", text, meta);
    promptInput.value = "";
    fileInput.value = "";
    updateAttachment();
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

attachButton.addEventListener("click", () => fileInput.click());
removeFileButton.addEventListener("click", () => {
  fileInput.value = "";
  updateAttachment();
});
fileInput.addEventListener("change", updateAttachment);
form.addEventListener("submit", handleSubmit);

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    promptInput.value = examples[button.dataset.example] || "";
    promptInput.focus();
  });
});

promptInput.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    form.requestSubmit();
  }
});

checkHealth();
