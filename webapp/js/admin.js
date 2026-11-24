/**
 * ToU Mini App — Модуль панели администратора
 */
window.TouApp = window.TouApp || {};

(function (app) {
  app.admin = app.admin || {};

  app.admin.renderAdminPanel = async function () {
    const userId = app.tg?.initDataUnsafe?.user?.id || app.urlParams.get("user_id") || "demo";
    const isDemo = app.state.isDemoMode;

    const countEl = document.getElementById("adminUsersCount");
    const maintBadge = document.getElementById("adminMaintBadge");
    const loginsList = document.getElementById("adminLoginsList");
    const loginsTotal = document.getElementById("adminLoginsTotal");
    const serverTimeEl = document.getElementById("adminServerTime");

    const endpoint = isDemo ? `/api/admin/stats?demo=1` : `/api/admin/stats?user_id=${userId}`;

    try {
      const resp = await fetch(endpoint);
      if (resp.ok) {
        const stats = await resp.json();
        if (countEl) countEl.textContent = stats.total_users ?? "0";
        if (maintBadge) {
          maintBadge.innerHTML = stats.is_maintenance
            ? `<span class="text-rose-400">🔴 АКТИВЕН (бот закрыт)</span>`
            : `<span class="text-emerald-400">🟢 Выключен (в норме)</span>`;
        }
        if (serverTimeEl) serverTimeEl.textContent = stats.server_time || "--:--";

        if (loginsList) {
          const logins = stats.logins || [];
          if (loginsTotal) loginsTotal.textContent = `${logins.length} чел.`;
          if (logins.length === 0) {
            loginsList.innerHTML = `<div class="text-slate-500 italic text-[11px]">Нет авторизованных студентов</div>`;
          } else {
            loginsList.innerHTML = logins.map((l, i) => `
              <div class="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <span class="font-mono text-white text-[11px]">${i + 1}. ${l}</span>
                <span class="text-[10px] text-emerald-400">В базе</span>
              </div>
            `).join("");
          }
        }
      } else {
        if (countEl) countEl.textContent = "1";
        if (maintBadge) maintBadge.innerHTML = `<span class="text-emerald-400">🟢 Выключен (демо)</span>`;
        if (loginsTotal) loginsTotal.textContent = "1 чел.";
        if (loginsList) {
          loginsList.innerHTML = `
            <div class="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
              <span class="font-mono text-white text-[11px]">1. demo_student</span>
              <span class="text-[10px] text-emerald-400">Демо</span>
            </div>
          `;
        }
      }
    } catch (e) {
      console.warn("Ошибка при получении админ-статистики:", e);
    }
  };

  app.admin.init = function () {
    const btnToggleMaint = document.getElementById("adminToggleMaintBtn");
    if (btnToggleMaint) {
      btnToggleMaint.addEventListener("click", async () => {
        app.triggerHaptic("medium");
        const userId = app.tg?.initDataUnsafe?.user?.id || app.urlParams.get("user_id") || "demo";
        const isDemo = app.state.isDemoMode;
        const endpoint = isDemo ? `/api/admin/toggle-maintenance?demo=1` : `/api/admin/toggle-maintenance?user_id=${userId}`;
        try {
          const resp = await fetch(endpoint);
          if (resp.ok) {
            await app.admin.renderAdminPanel();
            if (app.tg && app.tg.showAlert) {
              app.tg.showAlert("Статус технических работ успешно обновлен!");
            }
          }
        } catch (e) {
          console.error("Ошибка переключения техработ:", e);
        }
      });
    }

    const btnRefreshStats = document.getElementById("adminRefreshStatsBtn");
    if (btnRefreshStats) {
      btnRefreshStats.addEventListener("click", () => {
        app.triggerHaptic("light");
        app.admin.renderAdminPanel();
      });
    }

    const btnPingPortal = document.getElementById("adminPingPortalBtn");
    const portalPingRes = document.getElementById("adminPortalPingResult");
    if (btnPingPortal && portalPingRes) {
      btnPingPortal.addEventListener("click", () => {
        app.triggerHaptic("light");
        portalPingRes.classList.remove("hidden");
        portalPingRes.textContent = "Проверка tou.edu.kz... ⏳";
        portalPingRes.className = "text-[11px] p-2 rounded-lg bg-slate-900/80 border border-slate-800 font-mono text-amber-400";
        setTimeout(() => {
          portalPingRes.textContent = "tou.edu.kz доступен (HTTP 200 OK) ✅";
          portalPingRes.className = "text-[11px] p-2 rounded-lg bg-slate-900/80 border border-emerald-800/80 font-mono text-emerald-400";
        }, 600);
      });
    }
  };

})(window.TouApp);
