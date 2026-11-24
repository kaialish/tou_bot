/**
 * ToU Mini App — Утилиты, темы, хелперы и форматирование
 */
window.TouApp = window.TouApp || {};

(function (app) {
  // 1. Инициализация Telegram WebApp SDK
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    try {
      tg.enableClosingConfirmation();
    } catch (e) {}
  }
  app.tg = tg;

  // 2. Тактильный отклик (Haptic Feedback)
  app.triggerHaptic = function (type = "light") {
    try {
      if (tg?.HapticFeedback) {
        tg.HapticFeedback.impactOccurred(type);
      }
    } catch (e) {}
  };

  // 3. Темы оформления (Accent Themes)
  app.THEMES = {
    emerald: { name: "Изумруд", ringClass: "ring-emerald-400" },
    ocean: { name: "Океан", ringClass: "ring-sky-400" },
    purple: { name: "Неон", ringClass: "ring-purple-400" },
    sunset: { name: "Закат", ringClass: "ring-amber-400" },
    oled: { name: "OLED", ringClass: "ring-white" },
  };

  app.applyTheme = function (themeId) {
    if (!app.THEMES[themeId]) themeId = "emerald";
    document.documentElement.setAttribute("data-theme", themeId);
    if (document.body) {
      document.body.setAttribute("data-theme", themeId);
    }
    try {
      localStorage.setItem("tou_app_theme", themeId);
    } catch (e) {}

    const nameEl = document.getElementById("currentThemeName");
    if (nameEl) nameEl.textContent = app.THEMES[themeId].name;

    document.querySelectorAll(".theme-choice-btn").forEach((btn) => {
      const tid = btn.getAttribute("data-theme-btn");
      if (!tid || !app.THEMES[tid]) return;
      const circle = btn.querySelector("span:first-child");
      const label = btn.querySelector("span:last-child");
      const check = btn.querySelector(".theme-check-icon");
      const isCurrent = tid === themeId;

      if (circle) {
        circle.classList.remove(
          "ring-2",
          "ring-0",
          "ring-emerald-400",
          "ring-sky-400",
          "ring-purple-400",
          "ring-amber-400",
          "ring-white",
          "shadow-lg",
          "shadow-emerald-500/20"
        );
        if (isCurrent) {
          circle.classList.add("ring-2", app.THEMES[tid].ringClass);
        } else {
          circle.classList.add("ring-0");
        }
      }
      if (label) {
        label.className = `pointer-events-none text-[10px] font-medium ${isCurrent ? "text-white font-bold" : "text-slate-400"}`;
      }
      if (check) {
        check.classList.toggle("hidden", !isCurrent);
      }
    });

    // Мгновенное обновление динамических компонентов
    try {
      if (app.schedule?.renderWeekDaySelector) app.schedule.renderWeekDaySelector();
      if (app.schedule?.renderLiveWidget) app.schedule.renderLiveWidget();
      if (app.schedule?.renderLessons && app.state?.selectedDay) app.schedule.renderLessons(app.state.selectedDay);
      if (app.grades?.updateGradesPartButtons) app.grades.updateGradesPartButtons();
    } catch (e) {}
  };

  // 4. Цветовая дифференциация оценок
  app.getScoreColorClass = function (scoreVal) {
    if (scoreVal === null || scoreVal === undefined || scoreVal === "" || scoreVal === "—") {
      return {
        text: "text-slate-400",
        badge: "bg-slate-800 text-slate-400 border-slate-700/60"
      };
    }

    const num = parseFloat(String(scoreVal).replace(",", "."));
    if (isNaN(num)) {
      return {
        text: "text-slate-400",
        badge: "bg-slate-800 text-slate-400 border-slate-700/60"
      };
    }

    if (num === 0) {
      return {
        text: "text-white",
        badge: "bg-slate-800/90 text-white border-slate-600 font-semibold"
      };
    }

    if (num >= 70) {
      return {
        text: "score-green text-emerald-400 font-bold",
        badge: "score-badge-green font-semibold"
      };
    }

    if (num >= 51 && num <= 69.99) {
      return {
        text: "score-amber text-amber-400 font-bold",
        badge: "score-badge-amber font-semibold"
      };
    }

    return {
      text: "score-red text-rose-400 font-bold",
      badge: "score-badge-red font-semibold"
    };
  };

  // 5. Форматирование склонений
  app.getDaysWord = function (days) {
    const mod10 = days % 10;
    const mod100 = days % 100;
    if (mod100 >= 11 && mod100 <= 19) return "дней";
    if (mod10 === 1) return "день";
    if (mod10 >= 2 && mod10 <= 4) return "дня";
    return "дней";
  };

  app.getLessonsWord = function (count) {
    if (count === 1) return "пара";
    if (count >= 2 && count <= 4) return "пары";
    return "пар";
  };

  app.getTypeBadgeClass = function (typeStr = "") {
    const t = typeStr.toLowerCase();
    if (t.includes("лек")) return "badge-type-lecture";
    if (t.includes("лаб")) return "badge-type-lab";
    if (t.includes("прак") || t.includes("сем")) return "badge-type-practice";
    if (t.includes("дист") || t.includes("mook") || t.includes("моок")) return "badge-type-mook";
    return "badge-type-default";
  };

  app.expandLessonType = function (t = "") {
    const s = t.toLowerCase();
    if (s.includes("лек")) return "Лекция";
    if (s.includes("лаб")) return "Лабораторная";
    if (s.includes("прак") || s.includes("сем")) return "Практика";
    if (s.includes("дист") || s.includes("mook") || s.includes("моок")) return "MOOK";
    return t || "Занятие";
  };

  app.getKeyDateIcon = function (title = "") {
    const t = title.toLowerCase();
    if (t.includes("рк") || t.includes("рубежн")) return "📝";
    if (t.includes("экзамен") || t.includes("сессия")) return "🎓";
    if (t.includes("каникул")) return "🏖️";
    if (t.includes("аттестац")) return "📊";
    if (t.includes("практик")) return "💼";
    return "📌";
  };

  // 6. Даты и календарные утилиты
  app.getTodayWeekdayName = function () {
    const days = ["Воскресенье", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"];
    const todayIndex = new Date().getDay();
    if (todayIndex === 0 || todayIndex === 6) {
      return "Понедельник";
    }
    return days[todayIndex];
  };

  app.isRealCurrentDay = function (dayName) {
    const days = ["Воскресенье", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"];
    const todayIndex = new Date().getDay();
    if (todayIndex === 0 || todayIndex === 6) {
      return false;
    }
    return days[todayIndex] === dayName;
  };

})(window.TouApp);
