/**
 * ToU Mini App — Модуль расписания (дни недели, пары, текущий статус)
 */
window.TouApp = window.TouApp || {};

(function (app) {
  app.schedule = app.schedule || {};

  const WEEK_DAYS = [
    { key: "Понедельник", short: "Пн" },
    { key: "Вторник", short: "Вт" },
    { key: "Среда", short: "Ср" },
    { key: "Четверг", short: "Чт" },
    { key: "Пятница", short: "Пт" },
  ];

  // 1. Виджет «Текущая пара»
  app.schedule.renderLiveWidget = function () {
    const widget = app.state.data?.live_widget;
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
  };

  // 2. Селектор дней недели
  app.schedule.renderWeekDaySelector = function () {
    const container = document.getElementById("weekDaySelector");
    if (!container) return;
    container.innerHTML = "";

    WEEK_DAYS.forEach((d) => {
      const isSelected = d.key === app.state.selectedDay;
      const isToday = app.isRealCurrentDay(d.key);

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
        app.triggerHaptic("light");
        app.state.selectedDay = d.key;
        app.schedule.renderWeekDaySelector();
        app.schedule.renderLessons(d.key);
      });

      container.appendChild(btn);
    });
  };

  // 3. Список занятий на выбранный день
  app.schedule.renderLessons = function (dayName) {
    const selectedDayLabel = document.getElementById("selectedDayLabel");
    const lessonsCountLabel = document.getElementById("lessonsCountLabel");
    const container = document.getElementById("lessonsList");

    if (selectedDayLabel) selectedDayLabel.textContent = dayName;

    const lessons = app.state.data?.schedule?.[dayName] || [];
    if (lessonsCountLabel) lessonsCountLabel.textContent = `${lessons.length} ${app.getLessonsWord(lessons.length)}`;

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

    const isActuallyToday = app.isRealCurrentDay(dayName);
    const live = app.state.data?.live_widget;

    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();

    let activeLessonNumber = null;

    if (isActuallyToday) {
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
      const typeBadgeClass = app.getTypeBadgeClass(l.type);
      const isCurrent = (activeLessonNumber !== null) && (l.number === activeLessonNumber);

      const card = document.createElement("div");
      card.className = `p-3.5 rounded-xl border transition-all ${
        isCurrent
          ? "glass-card-active border-emerald-500/80 ring-2 ring-emerald-500/30 shadow-lg shadow-emerald-500/15"
          : "glass-card border-slate-800 hover:border-slate-700/80"
      }`;

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
              ${app.expandLessonType(l.type)}
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
  };

})(window.TouApp);
