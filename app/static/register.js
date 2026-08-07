const signupForm = document.querySelector("#signupForm");
const signupEmailInput = document.querySelector("#signupEmailInput");
const signupStatus = document.querySelector("#signupStatus");

function setSignupStatus(text, state = "") {
  signupStatus.textContent = text;
  signupStatus.className = `auth-status ${state}`.trim();
}

function prefillEmailFromUrl() {
  const params = new URLSearchParams(window.location.search);
  signupEmailInput.value = (params.get("email") || "").trim().toLowerCase();
  if (params.get("reason") === "unverified") {
    setSignupStatus(
      "This email needs verification before OTP login. Send the verification link below.",
      "error",
    );
  }
  signupEmailInput.focus();
}

async function requestSignupVerification(event) {
  event.preventDefault();
  const email = signupEmailInput.value.trim().toLowerCase();
  if (!email) {
    signupEmailInput.focus();
    return;
  }

  setSignupStatus("Sending verification link...", "info");
  const response = await fetch("/api/v1/auth/register-email", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    setSignupStatus(payload.detail || "Unable to send verification link.", "error");
    return;
  }

  const state = payload.status === "verified" ? "success" : "info";
  setSignupStatus(payload.message || "Verification link sent. Check your email.", state);
}

signupForm.addEventListener("submit", requestSignupVerification);
prefillEmailFromUrl();
