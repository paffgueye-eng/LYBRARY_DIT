(function () {
  "use strict";

  function togglePw(btn) {
    var wrap = btn.closest(".input-wrap");
    if (!wrap) return;
    var inp = wrap.querySelector('input[type="password"], input[type="text"]');
    if (!inp) return;
    var hidden = inp.type === "password";
    inp.type = hidden ? "text" : "password";
    btn.setAttribute("aria-label", hidden ? "Masquer le mot de passe" : "Afficher le mot de passe");
    btn.dataset.state = hidden ? "visible" : "hidden";
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".pw-toggle");
    if (btn) togglePw(btn);
  });

  var form = document.getElementById("loginForm");
  if (!form) return;

  form.addEventListener("submit", function () {
    var remember = document.getElementById("remember");
    var email = document.getElementById("email");
    if (!remember || !email) return;
    try {
      if (remember.checked) {
        localStorage.setItem("saved_email", email.value);
      } else {
        localStorage.removeItem("saved_email");
      }
    } catch (err) { /* private mode */ }
  });

  function clearSavedEmail() {
    try {
      localStorage.removeItem("saved_email");
    } catch (err) { /* ignore */ }
    var emailEl = document.getElementById("email");
    var rememberEl = document.getElementById("remember");
    if (emailEl) emailEl.value = "";
    if (rememberEl) rememberEl.checked = false;
  }

  var params = new URLSearchParams(window.location.search);
  if (params.has("fresh")) {
    clearSavedEmail();
  }

  var clearBtn = document.getElementById("clearSavedEmail");
  if (clearBtn) {
    clearBtn.addEventListener("click", function (e) {
      e.preventDefault();
      clearSavedEmail();
    });
  }

  try {
    var saved = localStorage.getItem("saved_email");
    var emailEl = document.getElementById("email");
    var rememberEl = document.getElementById("remember");
    if (saved && emailEl && !params.has("fresh")) {
      emailEl.value = saved;
      if (rememberEl) rememberEl.checked = true;
    }
  } catch (err) { /* ignore */ }
})();
