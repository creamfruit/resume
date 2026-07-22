/* Login/register screen: the entry point before either app's home
 * page. Stores the issued token in localStorage; every other page's
 * JS reads it from here and attaches it as `Authorization: Bearer` on
 * every fetch (see the shared `authFetch`/`requireToken` helpers in
 * home.js/app.js/event.js). Deliberately minimal, per the account
 * system's own scope: username + password only, no email
 * verification, password reset, or social login.
 *
 * This file is intentionally byte-identical between frontend_v2/ and
 * frontend/ (the new and legacy front doors) -- both call the same
 * relative /auth/register and /auth/login endpoints, so the same
 * credentials work on either app. The one difference between the two
 * copies is the #login-card element's `data-redirect` attribute (each
 * app's own home page), not this script.
 */
"use strict";

const $ = (id) => document.getElementById(id);

function showError(message) {
  $("login-error").textContent = message || "";
}

async function submitAuth(path) {
  const username = $("login-username").value.trim();
  const password = $("login-password").value;
  showError("");
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const body = await res.json();
    if (!res.ok || body.error) {
      showError(body.error || "Something went wrong.");
      return;
    }
    localStorage.setItem("runeted_token", body.token);
    localStorage.setItem("runeted_account", body.account);
    window.location.href = $("login-card").dataset.redirect || "/";
  } catch (err) {
    showError("Network error -- try again.");
  }
}

$("login-card").addEventListener("submit", (ev) => {
  ev.preventDefault();
  submitAuth("/auth/login");
});
$("register-submit").addEventListener("click", () => submitAuth("/auth/register"));
