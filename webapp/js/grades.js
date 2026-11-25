/**
 * ToU Mini App — Модуль успеваемости (журнал оценок, Р1/Р2)
 */
window.TouApp = window.TouApp || {};

(function (app) {
  app.grades = app.grades || {};

  // 1. Отрисовка списка дисциплин для выбранного рейтинга (Р1 или Р2)
  app.grades.renderGrades = function (part = 1) {
    const container = document.getElementById("gradesList");
    const anchorsContainer = document.getElementById("gradesSubjectAnchors");
    const weekEl = document.getElementById("currentWeekNum");
    if (weekEl) {
      const cw = app.state.data?.grades?.current_week ?? app.state.data?.academic_status?.current_week;
      weekEl.textContent = (cw !== undefined && cw !== null && cw !== "") ? String(cw) : "--";
    }
    if (!container) return;
    container.innerHTML = "";
    if (anchorsContainer) anchorsContainer.innerHTML = "";

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
      if (anchorsContainer) {
        const shortTitle = (c.title || `Предмет ${idx + 1}`).trim();
        const label = shortTitle.length > 18 ? `${shortTitle.slice(0, 17)}…` : shortTitle;
        const anchorBtn = document.createElement("button");
        anchorBtn.type = "button";
        anchorBtn.className = "flex-shrink-0 text-[11px] font-medium px-2.5 py-1.5 rounded-xl bg-slate-800/80 text-slate-300 hover:text-white border border-slate-700/60 active:scale-95 transition-all";
        anchorBtn.textContent = label;
        anchorBtn.title = shortTitle;
        anchorBtn.addEventListener("click", () => {
          app.triggerHaptic("light");
          const target = document.getElementById(`gradeCourse_${idx}`);
          if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
        });
        anchorsContainer.appendChild(anchorBtn);
      }

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
      card.id = `gradeCourse_${idx}`;
      card.className = "p-4 rounded-2xl glass-card border border-slate-800 space-y-3 scroll-mt-20";

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

    const floatingAnchorBtn = document.getElementById("gradesFloatingAnchorBtn");
    const anchorIcon = document.getElementById("gradesAnchorIcon");
    if (floatingAnchorBtn && anchorIcon) {
      const isNearCalculator = () => {
        if (window.scrollY <= 80) return false;
        const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 40;
        if (atBottom) return true;
        const calcCard = document.getElementById("gradeCalculatorCard");
        if (!calcCard) return false;
        const rect = calcCard.getBoundingClientRect();
        return rect.top <= window.innerHeight * 0.65;
      };

      const updateAnchorAppearance = () => {
        const atCalc = isNearCalculator();
        anchorIcon.textContent = atCalc ? "↑" : "🧮";
        floatingAnchorBtn.title = atCalc ? "Наверх к предметам" : "Перейти к калькулятору";
      };

      window.addEventListener("scroll", updateAnchorAppearance, { passive: true });
      updateAnchorAppearance();

      floatingAnchorBtn.addEventListener("click", () => {
        app.triggerHaptic("light");
        if (isNearCalculator()) {
          window.scrollTo({ top: 0, behavior: "smooth" });
        } else {
          if (app.calculator?.setCollapsed) {
            app.calculator.setCollapsed(false);
          }
          const calcCard = document.getElementById("gradeCalculatorCard");
          if (calcCard) {
            calcCard.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        }
      });
    }
  };

})(window.TouApp);
