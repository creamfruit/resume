(function () {
  if (window.__reconnectFabInit) return;
  window.__reconnectFabInit = true;

  function byId(id) { return document.getElementById(id); }

  function addMsg(container, text, isUser) {
    if (!container) return;
    var div = document.createElement("div");
    div.className = "rc-faq-msg" + (isUser ? " user" : "");
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  async function askFaq(question, body) {
    if (!question) return;
    addMsg(body, question, true);
    try {
      var res = await fetch("/faq", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question })
      });
      var out = await res.json().catch(function () { return {}; });
      addMsg(body, out.reply || "I'm not sure yet. Here are common topics I can help with.", false);
    } catch (e) {
      addMsg(body, "I'm not sure yet. Here are common topics I can help with.", false);
    }
  }

  function initFab() {
    var settingsBtn = byId("rc-fab-settings");
    var faqBtn = byId("rc-fab-faq");
    var faqPop = byId("rc-faq-pop");
    var faqClose = byId("rc-faq-close");
    var faqBody = byId("rc-faq-body");
    var faqForm = byId("rc-faq-form");
    var faqInput = byId("rc-faq-input");
    var chipsWrap = byId("rc-faq-chips");
    if (!settingsBtn || !faqBtn || !faqPop || !faqBody || !faqForm || !faqInput) return;

    if (!faqBody.childElementCount) {
      addMsg(faqBody, "Hi! I can help with account, matching, safety, circles, challenges, and points.", false);
    }

    settingsBtn.addEventListener("click", function () {
      var settingsTab = document.querySelector('.profile-tab-btn[data-tab="settings"]');
      if (settingsTab) {
        settingsTab.click();
        return;
      }
      window.location.href = "/profile#settings";
    });

    function openFaq() { faqPop.hidden = false; }
    function closeFaq() { faqPop.hidden = true; }
    faqBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      faqPop.hidden ? openFaq() : closeFaq();
    });
    faqClose && faqClose.addEventListener("click", closeFaq);

    faqForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var q = (faqInput.value || "").trim();
      faqInput.value = "";
      askFaq(q, faqBody);
    });

    chipsWrap && chipsWrap.addEventListener("click", function (e) {
      var chip = e.target.closest(".rc-chip");
      if (!chip) return;
      var q = chip.getAttribute("data-q") || chip.textContent || "";
      askFaq(q.trim(), faqBody);
    });

    document.addEventListener("click", function (e) {
      if (faqPop.hidden) return;
      if (e.target.closest("#rc-faq-pop") || e.target.closest("#rc-fab-faq")) return;
      closeFaq();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeFaq();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initFab);
  } else {
    initFab();
  }
})();
