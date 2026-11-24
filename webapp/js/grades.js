/**
 * ToU Mini App — Модуль успеваемости (журнал оценок, Р1/Р2)
 */
window.TouApp = window.TouApp || {};

(function (app) {
  app.grades = app.grades || {};

  // 1. Отрисовка списка дисциплин для выбранного рейтинга (Р1 или Р2)
  app.grades.renderGrades = function (part = 1) {
    const container = document.getElementById("gradesList");
    if (!container) return;
    container.innerHTML = "";

    const courses = app.state.data?.grades?.courses || [];
    if (courses.length === 0) {
      container.innerHTML = `
        <div class="text-center py-10 px-4 rounded-2xl glass-card">
          <span class="text-3xl">📊</span>
          <p class="font-semibold text-white mt-2">Журнал пуст</p>
          <p class="text-xs text-slate-400 mt-1">Оценки по дисциплинам пока не выставлены</p>
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

      const tuColor = app.getScoreColorClass(tu);
      const rkColor = app.getScoreColorClass(rk);
      const ratingColor = app.getScoreColorClass(rating);

      const teachersList = (c.teachers || [])
        .map(t => `${t.type}: <b>${t.fio}</b>`)
        .join(" • ");

      const card = document.createElement("div");
      card.className = "p-4 rounded-2xl glass-card border border-slate-800 space-y-3";

      card.innerHTML = `
        <div>
          <div class="flex items-start justify-between">
            <h3 class="font-bold text-sm text-white flex-1 pr-2 leading-snug">${c.title}</h3>
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
            ${app.grades.renderCourseActivities(p?.activities || c.activities, part)}
            <div class="pt-1.5 flex justify-end">
              <button type="button" data-calc-course="${idx}" class="text-[11px] font-medium text-emerald-400 hover:text-emerald-300 py-1 px-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 active:scale-95 transition-all flex items-center space-x-1">
                <span>🧮</span><span>Рассчитать в калькуляторе</span>
              </button>
            </div>
          </div>
        </details>
      `;

      const btnCalcCourse = card.querySelector(`[data-calc-course="${idx}"]`);
      if (btnCalcCourse) {
        btnCalcCourse.addEventListener("click", (e) => {
          e.stopPropagation();
          app.triggerHaptic("light");
          if (app.calculator?.fillFromCourse) {
            app.calculator.fillFromCourse(c, part);
          }
        });
      }

      container.appendChild(card);
    });
  };

  // 2. Отрисовка деталей недель по видам занятий
  app.grades.renderCourseActivities = function (activities = [], part = 1) {
    if (!activities || activities.length === 0) {
      return `<p class="text-slate-500 italic">Сведения по видам занятий отсутствуют</p>`;
    }

    return activities.map(act => {
      const weeks = (act.weeks || []).filter(w => {
        const weekNum = parseInt(w.week, 10);
        if (isNaN(weekNum)) return true;
        return part === 1 ? (weekNum >= 1 && weekNum <= 8) : (weekNum >= 9 && weekNum <= 15);
      });

      const avgColor = app.getScoreColorClass(act.avg);

      const weeksStr = weeks
        .map(w => {
          const c = app.getScoreColorClass(w.val);
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
  };

  // 3. Переключатель табов рейтинга (Р1 / Р2)
  app.grades.updateGradesPartButtons = function () {
    const btnPart1 = document.getElementById("btnPart1");
    const btnPart2 = document.getElementById("btnPart2");
    if (!btnPart1 || !btnPart2) return;

    if (app.state.selectedGradesPart === 1) {
      btnPart1.className = "flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all bg-emerald-500 text-white shadow-sm";
      btnPart2.className = "flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all text-slate-400 hover:text-white";
    } else {
      btnPart1.className = "flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all text-slate-400 hover:text-white";
      btnPart2.className = "flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all bg-emerald-500 text-white shadow-sm";
    }
  };

  app.grades.init = function () {
    const btnPart1 = document.getElementById("btnPart1");
    const btnPart2 = document.getElementById("btnPart2");

    if (btnPart1 && btnPart2) {
      btnPart1.addEventListener("click", () => {
        app.triggerHaptic("light");
        app.state.selectedGradesPart = 1;
        try { localStorage.setItem("tou_grades_part", "1"); } catch (e) {}
        app.grades.updateGradesPartButtons();
        app.grades.renderGrades(1);
      });

      btnPart2.addEventListener("click", () => {
        app.triggerHaptic("light");
        app.state.selectedGradesPart = 2;
        try { localStorage.setItem("tou_grades_part", "2"); } catch (e) {}
        app.grades.updateGradesPartButtons();
        app.grades.renderGrades(2);
      });
    }
  };

})(window.TouApp);
