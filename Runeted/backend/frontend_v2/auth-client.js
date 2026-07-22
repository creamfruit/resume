/* Shared token handling for every page that needs to be logged in.
 * Included via a <script> tag before each page's own script (this
 * frontend has no bundler/module system, so these are plain globals,
 * matching every other file here). Login itself lives in login.js;
 * this is what every OTHER page uses to attach the token and bounce
 * back to /login if it's missing or rejected.
 */
"use strict";

const AUTH_TOKEN_KEY = "runeted_token";
const AUTH_ACCOUNT_KEY = "runeted_account";

function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

function clearAuthToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_ACCOUNT_KEY);
}

// Call once at the top of a page's boot sequence: bounces to /login
// immediately if there's no token at all, so a logged-out visitor never
// even sees a flash of stale/empty game state.
function requireAuthToken() {
  if (!getAuthToken()) {
    window.location.href = "/login";
    return false;
  }
  return true;
}

// Every fetch to this app's own API should go through this instead of
// the bare fetch() -- it attaches the token, and a 401 (token missing,
// expired, or tampered) always means "log in again", never a retry.
async function authFetch(path, options) {
  const opts = Object.assign({}, options);
  opts.headers = Object.assign({}, opts.headers, { Authorization: `Bearer ${getAuthToken()}` });
  const res = await fetch(path, opts);
  if (res.status === 401) {
    clearAuthToken();
    window.location.href = "/login";
  }
  return res;
}
