/**
 * ToU Mini App — Модуль настроек, тем и конфиденциальности
 */
window.TouApp = window.TouApp || {};

(function (app) {
  app.settings = app.settings || {};

  const getActiveUserId = () => app.tg?.initDataUnsafe?.user?.id || app.urlParams.get("user_id");

  // 1. Отрисовка текущего состояния настроек
  app.settings.renderSettings = function () {
    const s = app.state.data?.settings || {};
    const notifEnabled = s.notifications_enabled !== false;
    const mookEnabled = s.notify_mook === true;

    const tNotif = document.getElementById("toggleNotifications");
    const tNotifThumb = document.getElementById("toggleNotificationsThumb");
    const tMook = document.getElementById("toggleMook");
    const tMookThumb = document.getElementById("toggleMookThumb");
    const mookRow = document.getElementById("mookToggleRow");

    if (tNotif) {
      tNotif.className = `w-12 h-6 rounded-full transition-colors duration-200 ${
        notifEnabled ? "bg-emerald-500" : "bg-slate-600"
      } relative flex-shrink-0`;
      if (tNotifThumb) tNotifThumb.style.transform = notifEnabled ? "translateX(24px)" : "translateX(0px)";
    }
    if (mookRow) {
      if (notifEnabled) {
        mookRow.classList.remove("hidden");
      } else {
        mookRow.classList.add("hidden");
      }
    }
    if (tMook) {
      tMook.className = `w-12 h-6 rounded-full transition-colors duration-200 ${
        mookEnabled ? "bg-emerald-500" : "bg-slate-600"
      } relative flex-shrink-0`;
      if (tMookThumb) tMookThumb.style.transform = mookEnabled ? "translateX(24px)" : "translateX(0px)";
    }

    const currentTheme = document.documentElement.getAttribute("data-theme") || "emerald";
    app.applyTheme(currentTheme);
  };

  app.settings.init = function () {
    const btnSettings = document.getElementById("btnSettings");
    const settingsModal = document.getElementById("settingsModal");
    const btnCloseSettings = document.getElementById("btnCloseSettings");

    if (btnSettings) {
      btnSettings.addEventListener("click", () => {
        app.triggerHaptic("light");
        app.settings.renderSettings();
        if (settingsModal) settingsModal.classList.remove("hidden");
      });
    }

    if (btnCloseSettings) {
      btnCloseSettings.addEventListener("click", () => {
        app.triggerHaptic("light");
        if (settingsModal) settingsModal.classList.add("hidden");
      });
    }

    if (settingsModal) {
      settingsModal.addEventListener("click", (e) => {
        if (e.target === settingsModal) {
          settingsModal.classList.add("hidden");
        }
      });
    }

    // Переключение уведомлений
    const toggleNotificationsBtn = document.getElementById("toggleNotifications");
    if (toggleNotificationsBtn) {
      toggleNotificationsBtn.addEventListener("click", async () => {
        app.triggerHaptic("medium");
        const uid = getActiveUserId();
        if (app.state.isDemoMode || !uid || uid === "demo") {
          const msg = "Настройки уведомлений доступны только в личном аккаунте.";
          if (app.tg?.showAlert) app.tg.showAlert(msg);
          else alert(msg);
          return;
        }
        try {
          const res = await fetch("/api/settings/toggle-notifications", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: uid })
          });
          if (res.ok) {
            const json = await res.json();
            if (!app.state.data.settings) app.state.data.settings = {};
            app.state.data.settings.notifications_enabled = json.notifications_enabled;
            app.settings.renderSettings();
          }
        } catch (err) {
          console.error("Ошибка переключения уведомлений:", err);
        }
      });
    }

    // Переключение MOOK
    const toggleMookBtn = document.getElementById("toggleMook");
    if (toggleMookBtn) {
      toggleMookBtn.addEventListener("click", async () => {
        app.triggerHaptic("medium");
        const uid = getActiveUserId();
        if (app.state.isDemoMode || !uid || uid === "demo") {
          const msg = "Настройки уведомлений доступны только в личном аккаунте.";
          if (app.tg?.showAlert) app.tg.showAlert(msg);
          else alert(msg);
          return;
        }
        try {
          const res = await fetch("/api/settings/toggle-mook", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: uid })
          });
          if (res.ok) {
            const json = await res.json();
            if (!app.state.data.settings) app.state.data.settings = {};
            app.state.data.settings.notify_mook = json.notify_mook;
            app.settings.renderSettings();
          }
        } catch (err) {
          console.error("Ошибка переключения MOOK:", err);
        }
      });
    }

    // Селектор тем оформления
    const themeContainer = document.getElementById("themeSelectorContainer");
    if (themeContainer) {
      themeContainer.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-theme-btn]");
        if (!btn) return;
        app.triggerHaptic("medium");
        const tid = btn.getAttribute("data-theme-btn");
        if (tid) app.applyTheme(tid);
      });
    }

    document.querySelectorAll(".theme-choice-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        app.triggerHaptic("medium");
        const tid = btn.getAttribute("data-theme-btn");
        if (tid) app.applyTheme(tid);
      });
    });

    const savedTheme = (() => {
      try {
        return localStorage.getItem("tou_app_theme") || "emerald";
      } catch (e) {
        return "emerald";
      }
    })();
    app.applyTheme(savedTheme);

    // Политика конфиденциальности
    const btnPrivacyPolicy = document.getElementById("btnPrivacyPolicy");
    const privacyPolicyModal = document.getElementById("privacyPolicyModal");
    const btnClosePrivacy = document.getElementById("btnClosePrivacy");
    const privacyPolicyText = document.getElementById("privacyPolicyText");

    if (btnPrivacyPolicy) {
      btnPrivacyPolicy.addEventListener("click", async () => {
        app.triggerHaptic("light");
        if (privacyPolicyText && !privacyPolicyText.textContent.trim()) {
          try {
            const res = await fetch("/api/privacy-policy");
            if (res.ok) {
              const json = await res.json();
              const cleanText = (json.policy || "")
                .replace(/<b>/g, "")
                .replace(/<\/b>/g, "")
                .replace(/<i>/g, "")
                .replace(/<\/i>/g, "")
                .replace(/<[^>]+>/g, "");
              privacyPolicyText.textContent = cleanText;
            }
          } catch (err) {
            console.error("Ошибка загрузки политики:", err);
            privacyPolicyText.textContent = "Не удалось загрузить политику конфиденциальности.";
          }
        }
        if (privacyPolicyModal) privacyPolicyModal.classList.remove("hidden");
      });
    }

    if (btnClosePrivacy) {
      btnClosePrivacy.addEventListener("click", () => {
        app.triggerHaptic("light");
        if (privacyPolicyModal) privacyPolicyModal.classList.add("hidden");
      });
    }

    if (privacyPolicyModal) {
      privacyPolicyModal.addEventListener("click", (e) => {
        if (e.target === privacyPolicyModal) {
          privacyPolicyModal.classList.add("hidden");
        }
      });
    }

    // Удаление аккаунта / сброс авторизации
    const btnWipeAccount = document.getElementById("btnWipeAccount");
    if (btnWipeAccount) {
      btnWipeAccount.addEventListener("click", async () => {
        app.triggerHaptic("heavy");
        const uid = getActiveUserId();
        if (app.state.isDemoMode || !uid || uid === "demo") {
          const msg = "Вы находитесь в демо-режиме, удаление не требуется.";
          if (app.tg?.showAlert) app.tg.showAlert(msg);
          else alert(msg);
          return;
        }

        const confirmed = confirm("Вы действительно хотите удалить свои сохранённые данные авторизации из бота?");
        if (!confirmed) return;

        try {
          const res = await fetch("/api/settings/wipe-account", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: uid })
          });
          if (res.ok) {
            try { localStorage.removeItem("tou_cached_student_data_" + uid); } catch (e) {}
            if (app.tg?.showAlert) {
              app.tg.showAlert("✅ Ваши данные успешно удалены. Для повторного входа отправьте /start в боте.");
            } else {
              alert("✅ Ваши данные успешно удалены. Для повторного входа отправьте /start в боте.");
            }
            app.loadData(false, true);
          }
        } catch (err) {
          console.error("Ошибка удаления аккаунта:", err);
        }
      });
    }
  };

})(window.TouApp);
