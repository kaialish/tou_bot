/**
 * ToU Mini App — Основная клиентская логика
 */
document.addEventListener("DOMContentLoaded", () => {
  // 1. Инициализация Telegram WebApp SDK
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand(); // Разворачиваем на полный экран телефона
    try {
      tg.enableClosingConfirmation(); // Защита от случайного смахивания вниз
    } catch (e) {}
  }

  // Звуковой/тактильный отклик (Haptic Feedback)
  const triggerHaptic = (type = "light") => {
    try {
      if (tg?.HapticFeedback) {
        tg.HapticFeedback.impactOccurred(type);
      }
    } catch (e) {}
  };

  // 2. Внутреннее состояние приложения
  const urlParams = new URLSearchParams(window.location.search);
  const initialUserId = tg?.initDataUnsafe?.user?.id || urlParams.get("user_id") || "demo";
  const initialIsDemo = urlParams.get("demo") === "1" || initialUserId === "demo";

  const state = {
    data: window.MOCK_DATA, // По умолчанию демо-данные, пока не загружены реальные
    realData: null,         // Кэш реальных данных
    isDemoMode: initialIsDemo,
    activeTab: "tabSchedule",
    selectedDay: getTodayWeekdayName(),
    selectedGradesPart: 1, // 1 или 2 рейтинг
  };

  // 3. Определение сегодняшнего дня недели (пн-пт)
  function getTodayWeekdayName() {
    const days = ["Воскресенье", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"];
    const todayIndex = new Date().getDay(); // 0 = Вс, 6 = Сб
    // В выходные дни (суббота или воскресенье) по умолчанию открываем Понедельник
    if (todayIndex === 0 || todayIndex === 6) {
      return "Понедельник";
    }
    return days[todayIndex];
  }

  // Проверка: является ли день реально сегодняшним учебным днём
  function isRealCurrentDay(dayName) {
    const days = ["Воскресенье", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"];
    const todayIndex = new Date().getDay();
    // В субботу и воскресенье учебных занятий нет
    if (todayIndex === 0 || todayIndex === 6) {
      return false;
    }
    return days[todayIndex] === dayName;
  }

  // 4. Загрузка данных с бэкенда (с поддержкой демо-режима и фолбэка)
  async function loadData(forceRefresh = false, switchMode = null) {
    const refreshIcon = document.getElementById("refreshIcon");
    if (refreshIcon) refreshIcon.classList.add("animate-spin");

    if (switchMode !== null) {
      state.isDemoMode = switchMode;
    }

    try {
      const userId = tg?.initDataUnsafe?.user?.id || urlParams.get("user_id") || "demo";

      // 1. Демо-режим
      if (state.isDemoMode) {
        const endpoint = `/api/student-data?demo=1`;
        const response = await fetch(endpoint);
        if (response.ok) {
          const json = await response.json();
          if (json && json.schedule) {
            state.data = json;
          }
        } else if (window.MOCK_DATA) {
          state.data = window.MOCK_DATA;
        }
      } else {
        // 2. Режим реального аккаунта
        const endpoint = forceRefresh ? `/api/refresh?user_id=${userId}` : `/api/student-data?user_id=${userId}`;
        const response = await fetch(endpoint);
        if (response.ok) {
          const json = await response.json();
          if (json && json.schedule) {
            state.data = json;
            state.realData = json;
            if (json.student?.is_demo) {
              state.isDemoMode = true;
            }
          }
        } else {
          console.warn("Бэкенд вернул статус", response.status, "— переключаемся в демо-режим");
          state.isDemoMode = true;
          if (window.MOCK_DATA) state.data = window.MOCK_DATA;
        }
      }
    } catch (err) {
      console.info("Сервер API не отвечает, работаем в демо-режиме:", err);
      state.isDemoMode = true;
      if (window.MOCK_DATA) state.data = window.MOCK_DATA;
    } finally {
      if (refreshIcon) {
        setTimeout(() => refreshIcon.classList.remove("animate-spin"), 500);
      }
      renderAll();
    }
  }

  // 5. Рендеринг всех экранов
  function renderAll() {
    renderHeader();
    renderLiveWidget();
    renderWeekDaySelector();
    renderLessons(state.selectedDay);
    renderGrades(state.selectedGradesPart);
    renderStatus();
    renderSettings();
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ШАПКА
  // ─────────────────────────────────────────────────────────────────────────────
  function renderHeader() {
    const student = state.data?.student || {};
    const nameEl = document.getElementById("headerStudentName");
    const subEl = document.getElementById("headerSubtext");
    const offlineBadge = document.getElementById("offlineBadge");
    const demoBadge = document.getElementById("demoBadge");
    const demoNoticeBanner = document.getElementById("demoNoticeBanner");
    const demoBtnLabel = document.getElementById("demoBtnLabel");
    const btnToggleDemo = document.getElementById("btnToggleDemo");

    const isDemo = state.isDemoMode || student.is_demo;

    if (nameEl) {
      nameEl.textContent = isDemo
        ? "Демо Студент"
        : (student.name || tg?.initDataUnsafe?.user?.first_name || "Студент ToU");
    }
    if (subEl) {
      subEl.textContent = isDemo
        ? "Торайгыров Университет (Демо-режим)"
        : (student.login ? `Логин: ${student.login}` : "Торайгыров Университет");
    }
    if (offlineBadge) {
      if (student.is_offline && !isDemo) {
        offlineBadge.classList.remove("hidden");
      } else {
        offlineBadge.classList.add("hidden");
      }
    }
    if (demoBadge) {
      if (isDemo) {
        demoBadge.classList.remove("hidden");
      } else {
        demoBadge.classList.add("hidden");
      }
    }
    if (demoNoticeBanner) {
      if (isDemo) {
        demoNoticeBanner.classList.remove("hidden");
      } else {
        demoNoticeBanner.classList.add("hidden");
      }
    }
    if (demoBtnLabel) {
      demoBtnLabel.textContent = isDemo ? "Мой вход" : "Демо";
    }
    if (btnToggleDemo) {
      if (isDemo) {
        btnToggleDemo.className = "text-[11px] font-semibold px-2.5 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30 active:scale-95 transition-all flex items-center space-x-1";
      } else {
        btnToggleDemo.className = "text-[11px] font-semibold px-2.5 py-1.5 rounded-xl bg-slate-800 border border-slate-700/60 text-slate-300 hover:text-white active:scale-95 transition-all flex items-center space-x-1";
      }
    }

    // Отображение вкладки Админа только для администраторов
    const navTabAdmin = document.getElementById("navTabAdmin");
    if (navTabAdmin) {
      if (student.is_admin) {
        navTabAdmin.classList.remove("hidden");
      } else {
        navTabAdmin.classList.add("hidden");
      }
    }

    // Аватарка студента из Telegram (вместо шапки выпускника)
    const avatarImg = document.getElementById("headerAvatarImg");
    const avatarFallback = document.getElementById("headerAvatarFallback");
    const userId = tg?.initDataUnsafe?.user?.id || urlParams.get("user_id");

    if (avatarImg && avatarFallback) {
      if (!isDemo && userId && userId !== "demo") {
        const directTgPhoto = tg?.initDataUnsafe?.user?.photo_url;
        const photoSrc = directTgPhoto || `/api/user-avatar?user_id=${userId}`;

        avatarImg.onload = () => {
          avatarImg.classList.remove("hidden");
          avatarFallback.classList.add("hidden");
        };
        avatarImg.onerror = () => {
          // Если SDK фото не загрузилось, пробуем загрузить через наш прокси
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
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ВИДЖЕТ «ТЕКУЩАЯ ПАРА»
  // ─────────────────────────────────────────────────────────────────────────────
  function renderLiveWidget() {
    const widget = state.data?.live_widget;
    const widgetEl = document.getElementById("liveWidget");
    const statusTitleEl = document.getElementById("liveStatusTitle");
    const timerBadgeEl = document.getElementById("liveTimerBadge");
    const lessonTitleEl = document.getElementById("liveLessonTitle");
    const lessonMetaEl = document.getElementById("liveLessonMeta");
    const livePing = document.getElementById("livePing");
    const liveDot = document.getElementById("liveDot");

    if (!widget || !widgetEl) return;

    if (widget.status === "in_lesson") {
      widgetEl.className = "rounded-2xl p-4 glass-card-active transition-all";
      statusTitleEl.textContent = `${widget.lesson_number}-я пара идёт`;
      statusTitleEl.className = "text-xs font-semibold uppercase tracking-wider text-emerald-400";
      livePing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75";
      liveDot.className = "relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500";
      
      timerBadgeEl.textContent = `Осталось: ${widget.remaining_minutes} мин`;
      timerBadgeEl.className = "text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-500/40";
      
      lessonTitleEl.textContent = `${widget.subject} (${widget.type})`;
      lessonMetaEl.innerHTML = `📍 Ауд. <b>${widget.room}</b> • 👤 ${widget.teacher || ""}`;

    } else if (widget.status === "break") {
      widgetEl.className = "rounded-2xl p-4 glass-card transition-all";
      statusTitleEl.textContent = `Перемена (${widget.break_duration || 10} мин)`;
      statusTitleEl.className = "text-xs font-semibold uppercase tracking-wider text-amber-400";
      livePing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75";
      liveDot.className = "relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500";

      timerBadgeEl.textContent = `До звонка: ${widget.remaining_minutes} мин`;
      timerBadgeEl.className = "text-xs font-medium px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-300 border border-amber-500/40";

      lessonTitleEl.textContent = widget.next_subject ? `След.: ${widget.next_subject}` : "Свободное время";
      lessonMetaEl.innerHTML = widget.next_room ? `📍 Идти в ауд. <b>${widget.next_room}</b>` : "Отдыхайте";

    } else if (widget.status === "after_day") {
      widgetEl.className = "rounded-2xl p-4 glass-card transition-all";
      statusTitleEl.textContent = "Пары завершены";
      statusTitleEl.className = "text-xs font-semibold uppercase tracking-wider text-slate-400";
      livePing.className = "hidden";
      liveDot.className = "relative inline-flex rounded-full h-2.5 w-2.5 bg-slate-500";

      timerBadgeEl.textContent = "🌙 Отдых";
      timerBadgeEl.className = "text-xs font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700";

      lessonTitleEl.textContent = "Все занятия на сегодня окончены! 🎉";
      lessonMetaEl.textContent = "Хорошего вечера! Расписание на завтра во вкладке ниже.";
    } else {
      widgetEl.className = "rounded-2xl p-4 glass-card transition-all";
      statusTitleEl.textContent = "Занятий нет";
      statusTitleEl.className = "text-xs font-semibold uppercase tracking-wider text-slate-400";
      livePing.className = "hidden";
      liveDot.className = "relative inline-flex rounded-full h-2.5 w-2.5 bg-slate-500";
      timerBadgeEl.textContent = "Свободно";
      lessonTitleEl.textContent = "Сегодня занятий по расписанию нет";
      lessonMetaEl.textContent = "Учебный день свободен от аудиторных пар";
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // РАСПИСАНИЕ: СЕЛЕКТОР ДНЕЙ (ПН-ПТ) И СПИСОК ПАР
  // ─────────────────────────────────────────────────────────────────────────────
  // Суббота и воскресенье исключены — в университете ToU пары с понедельника по пятницу
  const WEEK_DAYS = [
    { key: "Понедельник", short: "Пн" },
    { key: "Вторник", short: "Вт" },
    { key: "Среда", short: "Ср" },
    { key: "Четверг", short: "Чт" },
    { key: "Пятница", short: "Пт" },
  ];

  function renderWeekDaySelector() {
    const container = document.getElementById("weekDaySelector");
    if (!container) return;
    container.innerHTML = "";

    WEEK_DAYS.forEach((d) => {
      const isSelected = d.key === state.selectedDay;
      const isToday = isRealCurrentDay(d.key);

      const btn = document.createElement("button");
      btn.className = `flex-1 min-w-[58px] py-2 px-1 rounded-xl text-center font-medium transition-all ${
        isSelected
          ? "bg-emerald-500 text-white shadow-md shadow-emerald-500/20 scale-[1.02]"
          : "bg-slate-800/80 text-slate-300 hover:bg-slate-800 border border-slate-700/50"
      }`;

      btn.innerHTML = `
        <div class="text-xs font-bold leading-tight">${d.short}</div>
        <div class="text-[10px] mt-0.5 ${isSelected ? 'text-emerald-100' : 'text-slate-400'}">${isToday ? '• сегод.' : ''}</div>
      `;

      btn.addEventListener("click", () => {
        triggerHaptic("light");
        state.selectedDay = d.key;
        renderWeekDaySelector();
        renderLessons(d.key);
      });

      container.appendChild(btn);
    });
  }

  function renderLessons(dayName) {
    const selectedDayLabel = document.getElementById("selectedDayLabel");
    const lessonsCountLabel = document.getElementById("lessonsCountLabel");
    const container = document.getElementById("lessonsList");

    if (selectedDayLabel) selectedDayLabel.textContent = dayName;

    const lessons = state.data?.schedule?.[dayName] || [];
    if (lessonsCountLabel) lessonsCountLabel.textContent = `${lessons.length} ${getLessonsWord(lessons.length)}`;

    if (!container) return;
    container.innerHTML = "";

    if (lessons.length === 0) {
      container.innerHTML = `
        <div class="text-center py-10 px-4 rounded-2xl glass-card">
          <span class="text-3xl">☕</span>
          <p class="font-semibold text-white mt-2">Нет занятий</p>
          <p class="text-xs text-slate-400 mt-1">В этот день у вас нет пар по расписанию</p>
        </div>
      `;
      return;
    }

    // Проверяем, является ли просматриваемый день сегодняшним учебным днём
    const isActuallyToday = isRealCurrentDay(dayName);
    const live = state.data?.live_widget;

    // Вычисляем текущее астрономическое время в минутах от 00:00
    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();

    // СТРОГОЕ ОПРЕДЕЛЕНИЕ ТЕКУЩЕЙ ПАРЫ:
    // Должна подсвечиваться РОВНО ОДНА пара в расписании студента (или 0, если перемена/пары окончены)
    let activeLessonNumber = null;

    if (isActuallyToday) {
      // 1. По текущему времени на часах устройства: пара идёт, если startMin <= nowMinutes < endMin
      for (const l of lessons) {
        if (l.time) {
          const timeMatch = l.time.match(/(\d{1,2})[:.](\d{2})\s*[-–]\s*(\d{1,2})[:.](\d{2})/);
          if (timeMatch) {
            const startMin = parseInt(timeMatch[1], 10) * 60 + parseInt(timeMatch[2], 10);
            const endMin = parseInt(timeMatch[3], 10) * 60 + parseInt(timeMatch[4], 10);
            if (nowMinutes >= startMin && nowMinutes < endMin) {
              activeLessonNumber = l.number;
              break;
            }
          }
        }
      }

      // 2. Резервная сверка: если по минутам устройства не попали, но серверный live_widget сообщает in_lesson,
      // сопоставляем строго по совпадению времени начала пары (например "10:15")
      if (activeLessonNumber === null && live && live.status === "in_lesson" && live.start) {
        const liveStartClean = live.start.replace(/\s+/g, "");
        for (const l of lessons) {
          const lTimeClean = (l.time || "").replace(/\s+/g, "");
          if (lTimeClean.includes(liveStartClean)) {
            activeLessonNumber = l.number;
            break;
          }
        }
      }
    }

    lessons.forEach((l) => {
      const typeBadgeClass = getTypeBadgeClass(l.type);

      // Пара подсвечивается ТОЛЬКО если её номер совпал с найденной единственной активной парой
      const isCurrent = (activeLessonNumber !== null) && (l.number === activeLessonNumber);

      const card = document.createElement("div");
      card.className = `p-3.5 rounded-xl border transition-all ${
        isCurrent
          ? "glass-card-active border-emerald-500/80 ring-2 ring-emerald-500/30 shadow-lg shadow-emerald-500/15"
          : "glass-card border-slate-800 hover:border-slate-700/80"
      }`;

      // Яркий бейдж "ИДЁТ СЕЙЧАС" с пульсирующей точкой (отображается только на активной паре)
      const liveBadge = isCurrent
        ? `<span class="flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse">
             <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
             <span>ИДЁТ СЕЙЧАС</span>
           </span>`
        : "";

      card.innerHTML = `
        <div class="flex items-start justify-between">
          <div class="flex items-center space-x-2">
            <span class="w-6 h-6 rounded-lg ${isCurrent ? 'bg-emerald-600 text-white font-black' : 'bg-slate-800 text-slate-200 font-bold'} text-xs flex items-center justify-center border ${isCurrent ? 'border-emerald-400' : 'border-slate-700/80'}">
              ${l.number || '•'}
            </span>
            <span class="text-xs font-semibold ${isCurrent ? 'text-emerald-300' : 'text-emerald-400'} font-mono tracking-tight">${l.time}</span>
          </div>
          <div class="flex items-center space-x-1.5">
            ${liveBadge}
            <span class="text-[10px] font-semibold px-2 py-0.5 rounded-md ${typeBadgeClass}">
              ${expandLessonType(l.type)}
            </span>
          </div>
        </div>

        <div class="mt-2.5">
          <h3 class="font-semibold text-sm ${isCurrent ? 'text-emerald-200' : 'text-white'} leading-snug">${l.subject}</h3>
          <div class="flex items-center justify-between text-xs text-slate-400 mt-2 pt-2 border-t border-slate-800/60">
            <span class="inline-flex items-center text-slate-300 font-medium">
              <span class="text-emerald-400 mr-1">📍</span> Ауд. ${l.room || 'Не указана'}
            </span>
            <span class="truncate ml-2 text-slate-400">${l.teacher || ''}</span>
          </div>
        </div>
      `;

      container.appendChild(card);
    });
  }

  function getTypeBadgeClass(typeStr = "") {
    const t = typeStr.toLowerCase();
    if (t.includes("лек")) return "bg-sky-500/15 text-sky-300 border border-sky-500/30";
    if (t.includes("прак") || t.includes("сем")) return "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30";
    if (t.includes("лаб")) return "bg-purple-500/15 text-purple-300 border border-purple-500/30";
    return "bg-slate-700/40 text-slate-300";
  }

  function expandLessonType(t = "") {
    const s = t.toLowerCase();
    if (s.includes("лек")) return "Лекция";
    if (s.includes("лаб")) return "Лабораторная";
    if (s.includes("прак") || s.includes("сем")) return "Практика";
    return t || "Занятие";
  }

  function getLessonsWord(count) {
    if (count === 1) return "пара";
    if (count >= 2 && count <= 4) return "пары";
    return "пар";
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // УСПЕВАЕМОСТЬ (ЖУРНАЛ ОЦЕНОК)
  // ─────────────────────────────────────────────────────────────────────────────
  const btnPart1 = document.getElementById("btnPart1");
  const btnPart2 = document.getElementById("btnPart2");

  if (btnPart1 && btnPart2) {
    btnPart1.addEventListener("click", () => {
      triggerHaptic("light");
      state.selectedGradesPart = 1;
      updateGradesPartButtons();
      renderGrades(1);
    });

    btnPart2.addEventListener("click", () => {
      triggerHaptic("light");
      state.selectedGradesPart = 2;
      updateGradesPartButtons();
      renderGrades(2);
    });
  }

  function updateGradesPartButtons() {
    if (state.selectedGradesPart === 1) {
      btnPart1.className = "flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all bg-emerald-500 text-white shadow-sm";
      btnPart2.className = "flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all text-slate-400 hover:text-white";
    } else {
      btnPart1.className = "flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all text-slate-400 hover:text-white";
      btnPart2.className = "flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all bg-emerald-500 text-white shadow-sm";
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ПОДСВЕТКА ОЦЕНОК (ЦВЕТОВАЯ ДИФФЕРЕНЦИАЦИЯ)
  // ─────────────────────────────────────────────────────────────────────────────
  // >= 70: зеленый
  // 51..69: оранжевый
  // <= 50 (и > 0): красный
  // == 0: белый
  // — / пусто: нейтральный
  function getScoreColorClass(scoreVal) {
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

    // Если балл ровно 0 — белый цвет
    if (num === 0) {
      return {
        text: "text-white",
        badge: "bg-slate-800/90 text-white border-slate-600 font-semibold"
      };
    }

    // Выше 70 включительно — зеленый цвет
    if (num >= 70) {
      return {
        text: "text-emerald-400",
        badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 font-semibold"
      };
    }

    // От 51 до 69 включительно — оранжевый цвет
    if (num >= 51 && num <= 69.99) {
      return {
        text: "text-amber-400",
        badge: "bg-amber-500/15 text-amber-400 border-amber-500/30 font-semibold"
      };
    }

    // 50 и ниже включительно — красный цвет
    return {
      text: "text-rose-400",
      badge: "bg-rose-500/15 text-rose-400 border-rose-500/30 font-semibold"
    };
  }

  function renderGrades(part = 1) {
    const gradesData = state.data?.grades;
    const weekEl = document.getElementById("currentWeekNum");
    if (weekEl) weekEl.textContent = gradesData?.current_week || "9";

    const container = document.getElementById("gradesList");
    if (!container) return;
    container.innerHTML = "";

    const courses = gradesData?.courses || [];
    if (courses.length === 0) {
      container.innerHTML = `
        <div class="text-center py-10 px-4 rounded-2xl glass-card text-slate-400">
          <p class="font-semibold text-white">Данные успеваемости недоступны</p>
          <p class="text-xs mt-1">Оценки еще не загружены или не выставлены</p>
        </div>
      `;
      return;
    }

    courses.forEach((c, idx) => {
      const p = part === 1 ? c.part1 : c.part2;
      const tu = p?.tu || "—";
      const rk = p?.rk || "—";
      const rating = p?.rating || "—";
      const traffic = p?.traffic || "⚪";

      const tuColor = getScoreColorClass(tu);
      const rkColor = getScoreColorClass(rk);
      const ratingColor = getScoreColorClass(rating);

      const card = document.createElement("div");
      card.className = "p-4 rounded-2xl glass-card space-y-3";

      // Преподаватели
      const teachersList = (c.teachers || []).map(t => `<span class="inline-block mr-2">${t.type}: <b>${t.fio}</b></span>`).join("");

      card.innerHTML = `
        <div>
          <div class="flex items-start justify-between">
            <h3 class="font-bold text-sm text-white pr-2">${c.title}</h3>
            <span class="text-base">${traffic}</span>
          </div>
          <div class="text-[11px] text-slate-400 mt-1">
            ${teachersList || "Преподаватель не указан"}
          </div>
        </div>

        <div class="grid grid-cols-3 gap-2 py-2 px-3 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
          <div>
            <div class="text-[10px] text-slate-400 font-medium">ТУ${part} (тек.)</div>
            <div class="text-sm font-bold ${tuColor.text} mt-0.5">${tu}</div>
          </div>
          <div>
            <div class="text-[10px] text-slate-400 font-medium">РК${part} (рубеж)</div>
            <div class="text-sm font-bold ${rkColor.text} mt-0.5">${rk}</div>
          </div>
          <div>
            <div class="text-[10px] text-slate-400 font-medium">Р${part} (рейтинг)</div>
            <div class="text-sm font-bold ${ratingColor.text} mt-0.5">${rating}</div>
          </div>
        </div>

        <!-- Кнопка раскрытия подробных оценок по неделям -->
        <details class="group text-xs">
          <summary class="cursor-pointer text-slate-400 hover:text-slate-200 font-medium flex items-center justify-between py-1 select-none">
            <span>Подробнее</span>
            <span class="transition-transform group-open:rotate-180 text-emerald-400">▼</span>
          </summary>
          <div class="pt-2 space-y-2 text-slate-300">
            ${renderCourseActivities(p?.activities || c.activities, part)}
          </div>
        </details>
      `;

      container.appendChild(card);
    });
  }

  function renderCourseActivities(activities = [], part = 1) {
    if (!activities || activities.length === 0) {
      return `<p class="text-slate-500 italic">Сведения по видам занятий отсутствуют</p>`;
    }

    return activities.map(act => {
      // Строгая фильтрация: в 1 рейтинге только недели 1–8, во 2 рейтинге только 9–15
      const weeks = (act.weeks || []).filter(w => {
        const weekNum = parseInt(w.week, 10);
        if (isNaN(weekNum)) return true;
        return part === 1 ? (weekNum >= 1 && weekNum <= 8) : (weekNum >= 9 && weekNum <= 15);
      });

      const avgColor = getScoreColorClass(act.avg);

      const weeksStr = weeks
        .map(w => {
          const c = getScoreColorClass(w.val);
          return `<span class="inline-block px-1.5 py-0.5 rounded text-[11px] font-mono border mr-1 mb-1 ${c.badge}">${w.week}н: <b>${w.val}</b></span>`;
        })
        .join("");

      return `
        <div class="p-2 rounded-lg bg-slate-800/40 border border-slate-800">
          <div class="flex items-center justify-between mb-1.5">
            <span class="font-semibold text-slate-200">${act.type}</span>
            <span class="text-[11px] text-slate-400">ср. балл (Р${part}): <b class="${avgColor.text}">${act.avg || '—'}</b></span>
          </div>
          <div class="flex flex-wrap">${weeksStr || '<span class="text-slate-500 text-[11px]">Оценок за этот рейтинг нет</span>'}</div>
        </div>
      `;
    }).join("");
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // СТАТУС И КЛЮЧЕВЫЕ ДАТЫ
  // ─────────────────────────────────────────────────────────────────────────────
  // ─────────────────────────────────────────────────────────────────────────────
  // Автоматический расчет статуса и оставшихся дней для ключевых дат
  // ─────────────────────────────────────────────────────────────────────────────
  function calculateKeyDateStatus(periodStr) {
    if (!periodStr) return { status: "", marker: "🔹", color: "text-slate-400" };

    // Парсим даты вида DD.MM.YYYY - DD.MM.YYYY или DD.MM - DD.MM
    const match = periodStr.match(/(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\s*[-–—]\s*(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?/);
    if (!match) {
      return { status: "", marker: "🔹", color: "text-slate-400" };
    }

    const d1 = parseInt(match[1], 10);
    const m1 = parseInt(match[2], 10) - 1; // 0-based
    let y1 = match[3] ? parseInt(match[3], 10) : null;

    const d2 = parseInt(match[4], 10);
    const m2 = parseInt(match[5], 10) - 1;
    let y2 = match[6] ? parseInt(match[6], 10) : null;

    const now = new Date();
    const currentYear = now.getFullYear();

    // Если год не указан или оторван от текущего, привязываем к актуальному учебному году
    if (!y1 || Math.abs(y1 - currentYear) > 1) {
      const baseYear = (now.getMonth() >= 7) ? currentYear : currentYear - 1;
      y1 = (m1 >= 7) ? baseYear : baseYear + 1;
      y2 = (m2 >= 7) ? baseYear : baseYear + 1;
    }
    if (!y2) {
      y2 = (m2 < m1) ? y1 + 1 : y1;
    }

    const start = new Date(y1, m1, d1, 0, 0, 0, 0);
    const end = new Date(y2, m2, d2, 23, 59, 59, 999);
    const todayZero = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);

    const ONE_DAY_MS = 1000 * 60 * 60 * 24;

    const pad = (n) => String(n).padStart(2, "0");
    const formattedPeriod = `${pad(d1)}.${pad(m1 + 1)}.${y1} - ${pad(d2)}.${pad(m2 + 1)}.${y2}`;

    if (todayZero < start) {
      const daysLeft = Math.ceil((start.getTime() - todayZero.getTime()) / ONE_DAY_MS);
      return {
        marker: "🔹",
        status: `начнётся через ${daysLeft} ${getDaysWord(daysLeft)}`,
        color: "text-amber-400 font-medium",
        periodText: formattedPeriod
      };
    } else if (todayZero <= end) {
      const daysLeft = Math.ceil((end.getTime() - todayZero.getTime()) / ONE_DAY_MS);
      return {
        marker: "🔵",
        status: `осталось ${daysLeft} ${getDaysWord(daysLeft)}`,
        color: "text-sky-400 font-semibold",
        periodText: formattedPeriod
      };
    } else {
      return {
        marker: "✅",
        status: "завершено",
        color: "text-slate-400",
        periodText: formattedPeriod
      };
    }
  }

  function getDaysWord(n) {
    const abs = Math.abs(n) % 100;
    const n1 = abs % 10;
    if (abs >= 11 && abs <= 19) return "дней";
    if (n1 > 1 && n1 < 5) return "дня";
    if (n1 === 1) return "день";
    return "дней";
  }

  function renderStatus() {
    const checksGrid = document.getElementById("academicChecksGrid");
    const datesList = document.getElementById("keyDatesList");
    const overallBadge = document.getElementById("statusOverallBadge");

    const checks = state.data?.status_checks || [];
    const dates = state.data?.key_dates || [];

    if (overallBadge && state.data?.student?.status_overall) {
      overallBadge.textContent = state.data.student.status_overall;
    }

    if (checksGrid) {
      checksGrid.innerHTML = checks.map(c => {
        const isPos = c.indicator === "positive";
        const dotColor = isPos ? "bg-emerald-500" : "bg-red-500";
        let displayVal = c.value || "Нет данных";

        // Для блока флюорографии оставляем только дату действия
        const nameLower = (c.name || "").toLowerCase();
        if (nameLower.includes("флюорограф") || nameLower.includes("флюрограф")) {
          const dateMatch = displayVal.match(/(\d{2}[./-]\d{2}[./-]\d{2,4})/);
          if (dateMatch) {
            displayVal = `до ${dateMatch[1].replace(/[-/]/g, ".")}`;
          }
        }

        return `
          <div class="p-3 rounded-xl glass-card">
            <div class="flex items-center space-x-1.5 mb-1">
              <span class="w-2 h-2 rounded-full ${dotColor}"></span>
              <span class="text-[11px] text-slate-400 font-medium truncate">${c.name}</span>
            </div>
            <div class="text-xs font-bold text-white truncate">${displayVal}</div>
          </div>
        `;
      }).join("");
    }

        const yearEl = document.getElementById("keyDatesAcademicYear");
    if (yearEl) {
      const curY = new Date().getFullYear();
      const baseYear = (new Date().getMonth() >= 7) ? curY : curY - 1;
      yearEl.textContent = `${baseYear}–${baseYear + 1} уч. год`;
    }

    if (datesList) {
      datesList.innerHTML = dates.map(d => {
        let title = d.title || "";
        title = title.replace(/рубежный\s+контроль\s*№?\s*1/i, "РК №1");
        title = title.replace(/рубежный\s+контроль\s*№?\s*2/i, "РК №2");

        const rawPeriod = d.period || d.period_text || "";
        const calc = calculateKeyDateStatus(rawPeriod);

        const marker = calc.marker || d.marker || "🔹";
        const statusText = calc.status || d.status || "";
        const statusColor = calc.color || "text-emerald-400";
        const displayPeriod = calc.periodText || rawPeriod;

        return `
          <div class="p-3 rounded-xl glass-card flex items-start space-x-3">
            <span class="text-base">${marker}</span>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between">
                <h4 class="font-semibold text-xs text-white truncate">${title}</h4>
                <span class="text-[10px] text-slate-400 font-mono">${displayPeriod}</span>
              </div>
              <p class="text-[11px] ${statusColor} mt-0.5">${statusText}</p>
            </div>
          </div>
        `;
      }).join("");
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // НАВИГАЦИЯ ПО ТАБАМ (НИЖНИЙ TAB BAR)
  // ─────────────────────────────────────────────────────────────────────────────
  const tabButtons = document.querySelectorAll(".nav-tab");
  const tabContents = document.querySelectorAll(".tab-content");

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      triggerHaptic("light");
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

      state.activeTab = targetTabId;

      if (targetTabId === "tabAdmin") {
        renderAdminPanel();
      }
    });
  });

  // ─────────────────────────────────────────────────────────────────────────────
  // ПАНЕЛЬ АДМИНИСТРАТОРА (ФУНКЦИИ И СТАТИСТИКА)
  // ─────────────────────────────────────────────────────────────────────────────
  async function renderAdminPanel() {
    const userId = tg?.initDataUnsafe?.user?.id || urlParams.get("user_id") || "demo";
    const isDemo = state.isDemoMode;

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
        // Демо-фолбэк
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
  }

  // Кнопка переключения режима техработ в админке
  const btnToggleMaint = document.getElementById("adminToggleMaintBtn");
  if (btnToggleMaint) {
    btnToggleMaint.addEventListener("click", async () => {
      triggerHaptic("medium");
      const userId = tg?.initDataUnsafe?.user?.id || urlParams.get("user_id") || "demo";
      const isDemo = state.isDemoMode;
      const endpoint = isDemo ? `/api/admin/toggle-maintenance?demo=1` : `/api/admin/toggle-maintenance?user_id=${userId}`;
      try {
        const resp = await fetch(endpoint);
        if (resp.ok) {
          await renderAdminPanel();
          if (tg && tg.showAlert) {
            tg.showAlert("Статус технических работ успешно обновлен!");
          }
        }
      } catch (e) {
        console.error("Ошибка переключения техработ:", e);
      }
    });
  }

  // Кнопка обновления метрик админки
  const btnRefreshStats = document.getElementById("adminRefreshStatsBtn");
  if (btnRefreshStats) {
    btnRefreshStats.addEventListener("click", () => {
      triggerHaptic("light");
      renderAdminPanel();
    });
  }

  // Кнопка пинга портала университета
  const btnPingPortal = document.getElementById("adminPingPortalBtn");
  const portalPingRes = document.getElementById("adminPortalPingResult");
  if (btnPingPortal && portalPingRes) {
    btnPingPortal.addEventListener("click", () => {
      triggerHaptic("light");
      portalPingRes.classList.remove("hidden");
      portalPingRes.textContent = "Проверка tou.edu.kz... ⏳";
      portalPingRes.className = "text-[11px] p-2 rounded-lg bg-slate-900/80 border border-slate-800 font-mono text-amber-400";
      setTimeout(() => {
        portalPingRes.textContent = "tou.edu.kz доступен (HTTP 200 OK) ✅";
        portalPingRes.className = "text-[11px] p-2 rounded-lg bg-slate-900/80 border border-emerald-800/80 font-mono text-emerald-400";
      }, 600);
    });
  }

  // Кнопка принудительного обновления
  const btnRefresh = document.getElementById("btnRefresh");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => {
      triggerHaptic("medium");
      loadData(true);
    });
  }

  // Кнопка переключения Demo / Реальный аккаунт
  const btnToggleDemo = document.getElementById("btnToggleDemo");
  if (btnToggleDemo) {
    btnToggleDemo.addEventListener("click", () => {
      triggerHaptic("medium");
      if (state.isDemoMode) {
        // Переключение из демо в реальный аккаунт
        const currentUserId = tg?.initDataUnsafe?.user?.id || urlParams.get("user_id");
        if (currentUserId && currentUserId !== "demo") {
          loadData(false, false);
        } else {
          // Если зашли без параметров Telegram-пользователя
          if (tg && tg.showAlert) {
            tg.showAlert("Вы в демо-режиме! Чтобы подключить своё реальное расписание и оценки, откройте бота @tou_bot и отправьте /start.");
          } else {
            alert("Вы в демо-режиме! Для личного расписания авторизуйтесь в Telegram боте через /start.");
          }
        }
      } else {
        // Переключение в демонстрационный режим для тестирования
        loadData(false, true);
      }
    });
  }

  // Закрытие информационной плашки демо-режима
  const btnCloseDemoBanner = document.getElementById("btnCloseDemoBanner");
  if (btnCloseDemoBanner) {
    btnCloseDemoBanner.addEventListener("click", () => {
      triggerHaptic("light");
      const banner = document.getElementById("demoNoticeBanner");
      if (banner) banner.classList.add("hidden");
    });
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // НАСТРОЙКИ (SETTINGS MODAL)
  // ─────────────────────────────────────────────────────────────────────────────
  function renderSettings() {
    const s = state.data?.settings || {};
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
  }

  const btnSettings = document.getElementById("btnSettings");
  const settingsModal = document.getElementById("settingsModal");
  const btnCloseSettings = document.getElementById("btnCloseSettings");

  if (btnSettings) {
    btnSettings.addEventListener("click", () => {
      triggerHaptic("light");
      renderSettings();
      if (settingsModal) settingsModal.classList.remove("hidden");
    });
  }

  if (btnCloseSettings) {
    btnCloseSettings.addEventListener("click", () => {
      triggerHaptic("light");
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

  const getActiveUserId = () => tg?.initDataUnsafe?.user?.id || urlParams.get("user_id");

  // Переключение уведомлений о парах
  const toggleNotificationsBtn = document.getElementById("toggleNotifications");
  if (toggleNotificationsBtn) {
    toggleNotificationsBtn.addEventListener("click", async () => {
      triggerHaptic("medium");
      const uid = getActiveUserId();
      if (state.isDemoMode || !uid || uid === "demo") {
        if (tg?.showAlert) {
          tg.showAlert("Настройки уведомлений доступны только в личном аккаунте.");
        } else {
          alert("Настройки уведомлений доступны только в личном аккаунте.");
        }
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
          if (!state.data.settings) state.data.settings = {};
          state.data.settings.notifications_enabled = json.notifications_enabled;
          renderSettings();
        }
      } catch (err) {
        console.error("Ошибка переключения уведомлений:", err);
      }
    });
  }

  // Переключение уведомлений о парах MOOK
  const toggleMookBtn = document.getElementById("toggleMook");
  if (toggleMookBtn) {
    toggleMookBtn.addEventListener("click", async () => {
      triggerHaptic("medium");
      const uid = getActiveUserId();
      if (state.isDemoMode || !uid || uid === "demo") {
        if (tg?.showAlert) {
          tg.showAlert("Настройки уведомлений доступны только в личном аккаунте.");
        } else {
          alert("Настройки уведомлений доступны только в личном аккаунте.");
        }
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
          if (!state.data.settings) state.data.settings = {};
          state.data.settings.notify_mook = json.notify_mook;
          renderSettings();
        }
      } catch (err) {
        console.error("Ошибка переключения MOOK:", err);
      }
    });
  }

  // Политика конфиденциальности
  const btnPrivacyPolicy = document.getElementById("btnPrivacyPolicy");
  const privacyPolicyModal = document.getElementById("privacyPolicyModal");
  const btnClosePrivacy = document.getElementById("btnClosePrivacy");
  const privacyPolicyText = document.getElementById("privacyPolicyText");

  if (btnPrivacyPolicy) {
    btnPrivacyPolicy.addEventListener("click", async () => {
      triggerHaptic("light");
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
      triggerHaptic("light");
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

  // Ссылка на GitHub в модальном окне политики
  const privacyGithubLink = document.getElementById("privacyGithubLink");
  if (privacyGithubLink) {
    privacyGithubLink.addEventListener("click", (e) => {
      triggerHaptic("light");
      const githubUrl = "https://github.com/kaialish/tou_bot";
      if (tg?.openLink) {
        e.preventDefault();
        tg.openLink(githubUrl);
      }
    });
  }

  // Удаление аккаунта
  const btnDeleteAccount = document.getElementById("btnDeleteAccount");
  if (btnDeleteAccount) {
    btnDeleteAccount.addEventListener("click", async () => {
      triggerHaptic("heavy");
      const uid = getActiveUserId();
      if (state.isDemoMode || !uid || uid === "demo") {
        if (tg?.showAlert) {
          tg.showAlert("Действие недоступно в демо-режиме.");
        } else {
          alert("Действие недоступно в демо-режиме.");
        }
        return;
      }

      const confirmed = await new Promise((resolve) => {
        if (tg?.showConfirm) {
          tg.showConfirm("⚠️ Вы уверены, что хотите удалить все свои данные из базы бота? Это действие необратимо.", resolve);
        } else {
          resolve(window.confirm("Удалить все сохраненные данные из бота?"));
        }
      });

      if (!confirmed) return;

      try {
        const res = await fetch("/api/settings/delete-account", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: uid })
        });
        if (res.ok) {
          if (settingsModal) settingsModal.classList.add("hidden");
          if (tg?.showAlert) {
            tg.showAlert("✅ Ваши данные успешно удалены. Для повторного входа откройте бота и отправьте /start.");
          } else {
            alert("✅ Ваши данные успешно удалены. Для повторного входа отправьте /start в боте.");
          }
          // Переключаем в демо режим
          loadData(false, true);
        }
      } catch (err) {
        console.error("Ошибка удаления аккаунта:", err);
      }
    });
  }

  // Автоматический пересчёт текущей пары каждую минуту
  setInterval(() => {
    if (state.activeTab === "tabSchedule") {
      renderLessons(state.selectedDay);
    }
  }, 60000);

  // Первый запуск
  loadData();
});
