/**
 * ToU Mini App — Управление состоянием и загрузка данных
 */
window.TouApp = window.TouApp || {};

(function (app) {
  const urlParams = new URLSearchParams(window.location.search);
  const initialUserId = app.tg?.initDataUnsafe?.user?.id || urlParams.get("user_id") || "demo";
  const initialIsDemo = urlParams.get("demo") === "1" || initialUserId === "demo";

  // Запоминаем последний выбор рейтинга студентом (Р1 или Р2)
  const savedGradesPart = localStorage.getItem("tou_grades_part");
  const initialGradesPart = (savedGradesPart === "2") ? 2 : 1;

  // Загружаем сохранённый кэш для мгновенного отображения без ожидания сети
  let initialData = window.MOCK_DATA;
  if (!initialIsDemo && initialUserId && initialUserId !== "demo") {
    try {
      const rawCache = localStorage.getItem("tou_cached_student_data_" + initialUserId);
      if (rawCache) {
        const parsed = JSON.parse(rawCache);
        if (parsed && parsed.schedule) initialData = parsed;
      }
    } catch (e) {}
  }

  app.urlParams = urlParams;
  app.initialUserId = initialUserId;

  app.state = {
    data: initialData,
    realData: (initialData !== window.MOCK_DATA) ? initialData : null,
    isDemoMode: initialIsDemo,
    activeTab: "tabSchedule",
    selectedDay: app.getTodayWeekdayName(),
    selectedGradesPart: initialGradesPart,
  };

  // Фолбэк на оффлайн-кэш при падении портала университета
  app.fallbackToOfflineCache = function (userId) {
    let localCached = null;
    try {
      const raw = localStorage.getItem("tou_cached_student_data_" + userId);
      if (raw) localCached = JSON.parse(raw);
    } catch (e) {}

    if (localCached && localCached.schedule) {
      console.info("Портал ToU недоступен: загружаем данные из сохраненного локального кэша");
      app.state.data = localCached;
      app.state.realData = localCached;
      app.state.isDemoMode = false;
      if (!app.state.data.student) app.state.data.student = {};
      app.state.data.student.is_offline = true;
    } else {
      console.warn("Локальный кэш отсутствует — переключаемся в демо-режим");
      app.state.isDemoMode = true;
      if (window.MOCK_DATA) app.state.data = window.MOCK_DATA;
    }
  };

  // Загрузка данных с бэкенда
  app.loadData = async function (forceRefresh = false, switchMode = null) {
    const refreshIcon = document.getElementById("refreshIcon");
    if (refreshIcon) refreshIcon.classList.add("animate-spin");

    if (switchMode !== null) {
      app.state.isDemoMode = switchMode;
    }

    const userId = app.tg?.initDataUnsafe?.user?.id || app.urlParams.get("user_id") || "demo";

    try {
      if (app.state.isDemoMode) {
        const endpoint = `/api/student-data?demo=1`;
        const response = await fetch(endpoint);
        if (response.ok) {
          const json = await response.json();
          if (json && json.schedule) {
            app.state.data = json;
          }
        } else if (window.MOCK_DATA) {
          app.state.data = window.MOCK_DATA;
        }
      } else {
        const endpoint = forceRefresh ? `/api/refresh?user_id=${userId}` : `/api/student-data?user_id=${userId}`;
        const response = await fetch(endpoint);
        if (response.ok) {
          const json = await response.json();
          if (json && json.schedule) {
            app.state.data = json;
            app.state.realData = json;
            if (json.student?.is_demo) {
              app.state.isDemoMode = true;
            } else {
              try {
                localStorage.setItem("tou_cached_student_data_" + userId, JSON.stringify(json));
              } catch (e) {}
            }
          }
        } else {
          console.warn("Бэкенд вернул статус", response.status, "— активируем оффлайн-кэш");
          app.fallbackToOfflineCache(userId);
        }
      }
    } catch (err) {
      console.info("Сервер или сеть недоступны, проверяем оффлайн-кэш:", err);
      app.fallbackToOfflineCache(userId);
    } finally {
      if (refreshIcon) {
        setTimeout(() => refreshIcon.classList.remove("animate-spin"), 500);
      }
      app.renderAll();
    }
  };

  // Отрисовка всех экранов
  app.renderAll = function () {
    app.renderHeader();
    if (app.schedule?.renderLiveWidget) app.schedule.renderLiveWidget();
    if (app.schedule?.renderWeekDaySelector) app.schedule.renderWeekDaySelector();
    if (app.schedule?.renderLessons) app.schedule.renderLessons(app.state.selectedDay);
    if (app.grades?.updateGradesPartButtons) app.grades.updateGradesPartButtons();
    if (app.grades?.renderGrades) app.grades.renderGrades(app.state.selectedGradesPart);
    if (app.status?.renderStatus) app.status.renderStatus();
    if (app.settings?.renderSettings) app.settings.renderSettings();
  };

  // Отрисовка шапки профиля
  app.renderHeader = function () {
    const student = app.state.data?.student || {};
    const nameEl = document.getElementById("headerStudentName");
    const subEl = document.getElementById("headerSubtext");
    const offlineBadge = document.getElementById("offlineBadge");
    const demoNoticeBanner = document.getElementById("demoNoticeBanner");
    const demoIcon = document.getElementById("demoIcon");
    const demoBtnLabel = document.getElementById("demoBtnLabel");
    const btnToggleDemo = document.getElementById("btnToggleDemo");

    const isDemo = app.state.isDemoMode || student.is_demo;

    if (nameEl) {
      nameEl.textContent = isDemo
        ? "Демо Студент"
        : (student.name || app.tg?.initDataUnsafe?.user?.first_name || "Студент ToU");
    }
    if (subEl) {
      subEl.textContent = isDemo
        ? "Торайгыров Университет (Демо-режим)"
        : (student.login ? `Логин: ${student.login}` : "Торайгыров Университет");
    }
    if (offlineBadge) {
      if (student.is_offline && !isDemo) {
        offlineBadge.classList.remove("hidden");
        if (student.last_updated) {
          offlineBadge.textContent = `Кэш: ${student.last_updated}`;
          offlineBadge.title = `Данные сохранены из кэша от ${student.last_updated}`;
        } else {
          offlineBadge.textContent = "Оффлайн";
        }
      } else {
        offlineBadge.classList.add("hidden");
      }
    }
    if (demoNoticeBanner) {
      if (isDemo) {
        demoNoticeBanner.classList.remove("hidden");
      } else {
        demoNoticeBanner.classList.add("hidden");
      }
    }
    if (demoIcon) {
      demoIcon.textContent = isDemo ? "👤" : "🎮";
    }
    if (demoBtnLabel) {
      demoBtnLabel.textContent = isDemo ? "Вход" : "Демо";
    }
    if (btnToggleDemo) {
      btnToggleDemo.title = isDemo ? "Войти в свой аккаунт" : "Переключить в демо-режим";
      if (isDemo) {
        btnToggleDemo.className = "text-[11px] font-semibold px-2.5 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30 active:scale-95 transition-all flex items-center space-x-1";
      } else {
        btnToggleDemo.className = "text-[11px] font-semibold px-2.5 py-1.5 rounded-xl bg-slate-800 border border-slate-700/60 text-slate-300 hover:text-white active:scale-95 transition-all flex items-center space-x-1";
      }
    }

    const navTabAdmin = document.getElementById("navTabAdmin");
    if (navTabAdmin) {
      if (student.is_admin) {
        navTabAdmin.classList.remove("hidden");
      } else {
        navTabAdmin.classList.add("hidden");
      }
    }

    const avatarImg = document.getElementById("headerAvatarImg");
    const avatarFallback = document.getElementById("headerAvatarFallback");
    const userId = app.tg?.initDataUnsafe?.user?.id || app.urlParams.get("user_id");

    if (avatarImg && avatarFallback) {
      if (!isDemo && userId && userId !== "demo") {
        const directTgPhoto = app.tg?.initDataUnsafe?.user?.photo_url;
        const photoSrc = directTgPhoto || `/api/user-avatar?user_id=${userId}`;

        avatarImg.onload = () => {
          avatarImg.classList.remove("hidden");
          avatarFallback.classList.add("hidden");
        };
        avatarImg.onerror = () => {
          if (directTgPhoto && !avatarImg.src.includes("/api/user-avatar")) {
            avatarImg.src = `/api/user-avatar?user_id=${userId}`;
          } else {
            avatarImg.classList.add("hidden");
            avatarFallback.classList.remove("hidden");
          }
        };
        avatarImg.src = photoSrc;
      } else {
        avatarImg.classList.add("hidden");
        avatarFallback.classList.remove("hidden");
      }
    }
  };

})(window.TouApp);
