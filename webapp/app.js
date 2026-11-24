/**
 * ToU Mini App — Главный файл приложения (точка входа и оркестрация модулей)
 */
/**
 * Загружает вынесенные HTML-фрагменты (калькулятор, админ-панель, модальные окна)
 * перед инициализацией модулей, чтобы все DOM-элементы гарантированно существовали.
 */
async function loadHtmlPartials() {
  const mounts = [
    { id: "calculatorMount", url: "/static/partials/calculator.html?v=2.6" },
    { id: "tabAdmin", url: "/static/partials/tab-admin.html?v=2.6" },
    { id: "modalsMount", url: "/static/partials/modals.html?v=2.6" },
  ];

  await Promise.all(
    mounts.map(async ({ id, url }) => {
      const el = document.getElementById(id);
      if (!el) return;
      try {
        const resp = await fetch(url);
        if (resp.ok) {
          el.innerHTML = await resp.text();
        }
      } catch (err) {
        console.error(`Ошибка загрузки ${url}:`, err);
      }
    })
  );
}

document.addEventListener("DOMContentLoaded", async () => {
  const app = window.TouApp;
  if (!app) {
    console.error("Ошибка: модуль TouApp не загружен");
    return;
  }

  // 0. Подгружаем HTML-партиалы до инициализации обработчиков
  await loadHtmlPartials();

  // 1. Инициализация подсистем
  if (app.grades?.init) app.grades.init();
  if (app.calculator?.init) app.calculator.init();
  if (app.admin?.init) app.admin.init();
  if (app.settings?.init) app.settings.init();

  // 2. Навигация по табам (нижний Tab Bar)
  const tabButtons = document.querySelectorAll(".nav-tab");
  const tabContents = document.querySelectorAll(".tab-content");

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      app.triggerHaptic("light");
      const targetTabId = btn.getAttribute("data-tab");

      tabButtons.forEach(b => {
        b.classList.remove("text-emerald-400");
        b.classList.add("text-slate-400");
      });
      btn.classList.remove("text-slate-400");
      btn.classList.add("text-emerald-400");

      tabContents.forEach(tc => tc.classList.add("hidden"));
      const activeEl = document.getElementById(targetTabId);
      if (activeEl) activeEl.classList.remove("hidden");

      app.state.activeTab = targetTabId;

      if (targetTabId === "tabAdmin" && app.admin?.renderAdminPanel) {
        app.admin.renderAdminPanel();
      }
    });
  });

  // 3. Кнопка принудительного обновления данных
  const btnRefresh = document.getElementById("btnRefresh");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => {
      app.triggerHaptic("medium");
      app.loadData(true);
    });
  }

  // 4. Кнопка переключения Demo / Реальный аккаунт
  const btnToggleDemo = document.getElementById("btnToggleDemo");
  if (btnToggleDemo) {
    btnToggleDemo.addEventListener("click", () => {
      app.triggerHaptic("medium");
      if (app.state.isDemoMode) {
        const currentUserId = app.tg?.initDataUnsafe?.user?.id || app.urlParams.get("user_id");
        if (currentUserId && currentUserId !== "demo") {
          app.loadData(false, false);
        } else {
          const msg = "Вы в демо-режиме! Чтобы подключить своё реальное расписание и оценки, откройте бота @tou_bot и отправьте /start.";
          if (app.tg?.showAlert) app.tg.showAlert(msg);
          else alert(msg);
        }
      } else {
        app.loadData(false, true);
      }
    });
  }

  // 5. Закрытие информационной плашки демо-режима
  const btnCloseDemoBanner = document.getElementById("btnCloseDemoBanner");
  if (btnCloseDemoBanner) {
    btnCloseDemoBanner.addEventListener("click", () => {
      app.triggerHaptic("light");
      const banner = document.getElementById("demoNoticeBanner");
      if (banner) banner.classList.add("hidden");
    });
  }

  // 6. Автоматический пересчёт текущей пары каждую минуту
  setInterval(() => {
    if (app.state.activeTab === "tabSchedule" && app.schedule?.renderLessons) {
      app.schedule.renderLessons(app.state.selectedDay);
    }
  }, 60000);

  // 7. Первый запуск загрузки данных
  app.loadData();
});
