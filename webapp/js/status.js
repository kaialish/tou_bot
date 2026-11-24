/**
 * ToU Mini App — Модуль академического статуса и ключевых дат
 */
window.TouApp = window.TouApp || {};

(function (app) {
  app.status = app.status || {};

  // 1. Автоматический расчет статуса и оставшихся дней для ключевых дат
  app.status.calculateKeyDateStatus = function (periodStr) {
    if (!periodStr) return { status: "", marker: "📌", color: "text-slate-400", state: "unknown" };

    const match = periodStr.match(/(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\s*[-–—]\s*(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?/);
    if (!match) {
      return { status: "", marker: "📌", color: "text-slate-400", state: "unknown", periodText: periodStr };
    }

    const d1 = parseInt(match[1], 10);
    const m1 = parseInt(match[2], 10) - 1;
    let y1 = match[3] ? parseInt(match[3], 10) : null;

    const d2 = parseInt(match[4], 10);
    const m2 = parseInt(match[5], 10) - 1;
    let y2 = match[6] ? parseInt(match[6], 10) : null;

    const now = new Date();
    const currentYear = now.getFullYear();

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
    const formattedPeriod = `${pad(d1)}.${pad(m1 + 1)} – ${pad(d2)}.${pad(m2 + 1)}.${y2}`;

    if (todayZero < start) {
      const daysLeft = Math.ceil((start.getTime() - todayZero.getTime()) / ONE_DAY_MS);
      return {
        marker: "🔹",
        status: `начнётся через ${daysLeft} ${app.getDaysWord(daysLeft)}`,
        color: "text-amber-400 font-medium",
        periodText: formattedPeriod,
        state: "upcoming",
        days: daysLeft
      };
    } else if (todayZero <= end) {
      const daysLeft = Math.ceil((end.getTime() - todayZero.getTime()) / ONE_DAY_MS);
      const totalDays = Math.max(1, Math.ceil((end.getTime() - start.getTime()) / ONE_DAY_MS));
      const elapsedDays = Math.max(0, Math.ceil((todayZero.getTime() - start.getTime()) / ONE_DAY_MS));
      const progressPercent = Math.min(100, Math.max(5, Math.round((elapsedDays / totalDays) * 100)));
      return {
        marker: "🔵",
        status: `осталось ${daysLeft} ${app.getDaysWord(daysLeft)}`,
        color: "text-sky-400 font-semibold",
        periodText: formattedPeriod,
        state: "active",
        days: daysLeft,
        progressPercent: progressPercent
      };
    } else {
      return {
        marker: "✅",
        status: "завершено",
        color: "text-slate-500",
        periodText: formattedPeriod,
        state: "completed"
      };
    }
  };

  // 2. Отрисовка академических проверок и ключевых дат
  app.status.renderStatus = function () {
    const checksGrid = document.getElementById("academicChecksGrid");
    const datesList = document.getElementById("keyDatesList");
    const overallBadge = document.getElementById("statusOverallBadge");

    const checks = app.state.data?.status_checks || [];
    const dates = app.state.data?.key_dates || [];

    if (overallBadge && app.state.data?.student?.status_overall) {
      overallBadge.textContent = app.state.data.student.status_overall;
    }

    if (checksGrid) {
      checksGrid.innerHTML = checks.map(c => {
        const isPos = c.indicator === "positive";
        const dotColor = isPos ? "status-dot-pos bg-emerald-500" : "status-dot-neg bg-red-500";
        let displayVal = c.value || "Нет данных";

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
      yearEl.textContent = `${baseYear}–${baseYear + 1}`;
    }

    if (datesList) {
      datesList.innerHTML = dates.map(d => {
        let title = d.title || "";
        title = title.replace(/рубежный\s+контроль\s*№?\s*1/i, "РК №1");
        title = title.replace(/рубежный\s+контроль\s*№?\s*2/i, "РК №2");

        const rawPeriod = d.period || d.period_text || "";
        const calc = app.status.calculateKeyDateStatus(rawPeriod);
        const icon = app.getKeyDateIcon(title);
        const displayPeriod = calc.periodText || rawPeriod;

        if (calc.state === "active") {
          return `
            <div class="p-3.5 rounded-2xl timeline-card timeline-card-active space-y-2">
              <div class="flex items-start justify-between">
                <div class="flex items-center space-x-2.5">
                  <span class="w-9 h-9 rounded-xl bg-sky-500/20 text-sky-300 border border-sky-400/40 flex items-center justify-center text-base shadow-sm">
                    ${icon}
                  </span>
                  <div>
                    <h4 class="font-bold text-xs text-white leading-tight">${title}</h4>
                    <span class="text-[10px] text-sky-300 font-mono mt-0.5 inline-block">📅 ${displayPeriod}</span>
                  </div>
                </div>
                <span class="flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 border border-sky-400/40">
                  <span class="w-1.5 h-1.5 rounded-full bg-sky-400 animate-ping"></span>
                  <span>СЕЙЧАС</span>
                </span>
              </div>
              <div class="timeline-progress">
                <div class="timeline-progress-fill" style="width: ${calc.progressPercent || 50}%"></div>
              </div>
              <div class="flex items-center justify-between text-[10px] text-slate-300 pt-0.5">
                <span class="text-sky-300 font-medium">⏳ Осталось ${calc.days} ${app.getDaysWord(calc.days)}</span>
                <span class="text-slate-400">${calc.progressPercent || 50}% пройдено</span>
              </div>
            </div>
          `;
        } else if (calc.state === "upcoming") {
          return `
            <div class="p-3 rounded-xl glass-card flex items-center justify-between space-x-3 border-slate-800 hover:border-slate-700">
              <div class="flex items-center space-x-2.5 min-w-0">
                <span class="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-300 border border-amber-500/30 flex items-center justify-center text-sm flex-shrink-0">
                  ${icon}
                </span>
                <div class="min-w-0">
                  <h4 class="font-semibold text-xs text-white truncate">${title}</h4>
                  <div class="text-[10px] text-slate-400 font-mono mt-0.5">📅 ${displayPeriod}</div>
                </div>
              </div>
              <span class="flex-shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                Через ${calc.days} ${app.getDaysWord(calc.days)}
              </span>
            </div>
          `;
        } else {
          return `
            <div class="p-3 rounded-xl glass-card flex items-center justify-between space-x-3 border-slate-800/60 opacity-60">
              <div class="flex items-center space-x-2.5 min-w-0">
                <span class="w-8 h-8 rounded-xl bg-slate-800 text-slate-400 border border-slate-700/60 flex items-center justify-center text-sm flex-shrink-0">
                  ✓
                </span>
                <div class="min-w-0">
                  <h4 class="font-medium text-xs text-slate-300 truncate">${title}</h4>
                  <div class="text-[10px] text-slate-500 font-mono mt-0.5">${displayPeriod}</div>
                </div>
              </div>
              <span class="flex-shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/60">
                Завершено
              </span>
            </div>
          `;
        }
      }).join("");
    }
  };

})(window.TouApp);
