/**
 * ToU Mini App — Модуль калькулятора баллов (лекции, практика, ТУ, РК, допуск к экзамену)
 */
window.TouApp = window.TouApp || {};

(function (app) {
  app.calculator = app.calculator || {};

  app.calculator.init = function () {
    const tabR1 = document.getElementById("calcTabR1");
    const tabR2 = document.getElementById("calcTabR2");
    const tabRd = document.getElementById("calcTabRd");

    const formulaText = document.getElementById("calcFormulaText");
    const ratingSection = document.getElementById("calcRatingSection");
    const rdSection = document.getElementById("calcRdSection");

    const lectureCells = document.getElementById("calcLectureCells");
    const lectureAvg = document.getElementById("calcLectureAvg");
    const practiceCells = document.getElementById("calcPracticeCells");
    const practiceAvg = document.getElementById("calcPracticeAvg");

    const tuValue = document.getElementById("calcTuValue");
    const tuSub = document.getElementById("calcTuSub");

    const rkLabel = document.getElementById("calcRkLabel");
    const rkInput = document.getElementById("calcRkInput");

    const resultLabel = document.getElementById("calcResultLabel");
    const resultSubtext = document.getElementById("calcResultSubtext");
    const resultValue = document.getElementById("calcResultValue");
    const resultStatus = document.getElementById("calcResultStatus");

    const rdInputR1 = document.getElementById("calcRdInputR1");
    const rdInputR2 = document.getElementById("calcRdInputR2");
    const rdValue = document.getElementById("calcRdValue");
    const rdStatus = document.getElementById("calcRdStatus");
    const examTargets = document.getElementById("calcExamTargets");
    const btnReset = document.getElementById("btnResetCalc");
    const headerToggle = document.getElementById("calcHeaderToggle");
    const btnToggleCalc = document.getElementById("btnToggleCalc");
    const calcToggleLabel = document.getElementById("calcToggleLabel");
    const calcToggleChevron = document.getElementById("calcToggleChevron");
    const collapsibleBody = document.getElementById("calcCollapsibleBody");

    if (!tabR1 || !lectureCells || !practiceCells) return;

    function setCollapsed(collapsed, save = true) {
      if (!collapsibleBody) return;
      collapsibleBody.classList.toggle("hidden", collapsed);
      if (btnReset) btnReset.classList.toggle("hidden", collapsed);
      if (calcToggleChevron) calcToggleChevron.classList.toggle("rotate-180", !collapsed);
      if (calcToggleLabel) calcToggleLabel.textContent = collapsed ? "Развернуть" : "Свернуть";
      if (btnToggleCalc) btnToggleCalc.setAttribute("aria-expanded", String(!collapsed));
      if (save) {
        try { localStorage.setItem("tou_calc_collapsed", collapsed ? "true" : "false"); } catch (e) {}
      }
    }

    app.calculator.setCollapsed = setCollapsed;

    if (headerToggle) {
      headerToggle.addEventListener("click", () => {
        app.triggerHaptic("light");
        const isCurrentlyCollapsed = collapsibleBody ? collapsibleBody.classList.contains("hidden") : false;
        setCollapsed(!isCurrentlyCollapsed);
      });
    }

    try {
      const savedCollapsed = localStorage.getItem("tou_calc_collapsed");
      setCollapsed(savedCollapsed !== "false", false);
    } catch (e) {
      setCollapsed(true, false);
    }

    let currentMode = "r1"; // 'r1' | 'r2' | 'rd'
    const memory = {
      r1: {
        lectures: {},
        practices: {},
        rk: "",
        rating: null,
      },
      r2: {
        lectures: {},
        practices: {},
        rk: "",
        rating: null,
      },
    };

    function getWeeksList(mode) {
      return mode === "r1" ? [1, 2, 3, 4, 5, 6, 7, 8] : [9, 10, 11, 12, 13, 14, 15];
    }

    function renderWeekCells() {
      if (currentMode === "rd") return;
      const weeks = getWeeksList(currentMode);
      const modeData = memory[currentMode];

      lectureCells.innerHTML = weeks.map(w => {
        const rawVal = modeData.lectures[w];
        const val = (rawVal !== undefined && rawVal !== null && rawVal !== "" && Number(rawVal) !== 0) ? rawVal : "";
        return `
          <div class="calc-cell-box flex flex-col items-center p-1 rounded-xl bg-slate-900/90 border border-slate-800 focus-within:border-emerald-500/80 transition-all">
            <span class="text-[10px] text-slate-400 font-mono mb-1">${w}н</span>
            <input type="number" min="0" max="100" inputmode="decimal" placeholder="0"
              data-type="lectures" data-week="${w}" value="${val}"
              class="calc-cell-input w-full text-center py-1 text-xs font-bold rounded-lg" />
          </div>
        `;
      }).join("");

      practiceCells.innerHTML = weeks.map(w => {
        const rawVal = modeData.practices[w];
        const val = (rawVal !== undefined && rawVal !== null && rawVal !== "" && Number(rawVal) !== 0) ? rawVal : "";
        return `
          <div class="calc-cell-box flex flex-col items-center p-1 rounded-xl bg-slate-900/90 border border-slate-800 focus-within:border-emerald-500/80 transition-all">
            <span class="text-[10px] text-slate-400 font-mono mb-1">${w}н</span>
            <input type="number" min="0" max="100" inputmode="decimal" placeholder="0"
              data-type="practices" data-week="${w}" value="${val}"
              class="calc-cell-input w-full text-center py-1 text-xs font-bold rounded-lg" />
          </div>
        `;
      }).join("");
    }

    function handleCellInput(e) {
      const input = e.target;
      if (!input.classList.contains("calc-cell-input")) return;
      const type = input.getAttribute("data-type");
      const week = parseInt(input.getAttribute("data-week"), 10);
      const raw = input.value.trim().replace(",", ".");
      if (raw === "") {
        delete memory[currentMode][type][week];
      } else {
        const num = parseFloat(raw);
        if (!isNaN(num) && num >= 0 && num <= 100) {
          memory[currentMode][type][week] = num;
        } else {
          delete memory[currentMode][type][week];
        }
      }
      calculateRating();
    }

    function handleCellFocus(e) {
      const input = e.target;
      if (!input.classList.contains("calc-cell-input")) return;
      input.select();
    }

    lectureCells.addEventListener("input", handleCellInput);
    practiceCells.addEventListener("input", handleCellInput);
    lectureCells.addEventListener("focusin", handleCellFocus);
    practiceCells.addEventListener("focusin", handleCellFocus);

    function calculateRating() {
      if (currentMode === "rd") {
        calculateAdmission();
        return;
      }

      const modeData = memory[currentMode];

      // Средний балл лекций
      const lecScores = Object.values(modeData.lectures).filter(v => typeof v === "number" && !isNaN(v) && v >= 0);
      let avgLec = null;
      if (lecScores.length > 0) {
        const sum = lecScores.reduce((a, b) => a + b, 0);
        avgLec = Math.round((sum / lecScores.length) * 10) / 10;
        lectureAvg.textContent = avgLec;
        const c = app.getScoreColorClass(avgLec);
        lectureAvg.className = `font-bold ${c.text}`;
      } else {
        lectureAvg.textContent = "—";
        lectureAvg.className = "font-bold text-slate-400";
      }

      // Средний балл практики
      const pracScores = Object.values(modeData.practices).filter(v => typeof v === "number" && !isNaN(v) && v >= 0);
      let avgPrac = null;
      if (pracScores.length > 0) {
        const sum = pracScores.reduce((a, b) => a + b, 0);
        avgPrac = Math.round((sum / pracScores.length) * 10) / 10;
        practiceAvg.textContent = avgPrac;
        const c = app.getScoreColorClass(avgPrac);
        practiceAvg.className = `font-bold ${c.text}`;
      } else {
        practiceAvg.textContent = "—";
        practiceAvg.className = "font-bold text-slate-400";
      }

      // Текущая успеваемость (ТУ)
      let tu = null;
      if (avgLec !== null && avgPrac !== null) {
        tu = Math.round(((avgLec + avgPrac) / 2) * 10) / 10;
        if (tuSub) tuSub.textContent = "ср. лек+прак";
      } else if (avgLec !== null) {
        tu = avgLec;
        if (tuSub) tuSub.textContent = "только лекции";
      } else if (avgPrac !== null) {
        tu = avgPrac;
        if (tuSub) tuSub.textContent = "только практика";
      } else {
        if (tuSub) tuSub.textContent = "ср. лек+прак";
      }

      if (tu !== null) {
        tuValue.textContent = tu;
        const c = app.getScoreColorClass(tu);
        tuValue.className = `text-xl font-black ${c.text}`;
      } else {
        tuValue.textContent = "—";
        tuValue.className = "text-xl font-black text-white";
      }

      // Рубежный контроль (РК)
      const rkRaw = (rkInput.value || "").trim().replace(",", ".");
      let rk = null;
      if (rkRaw !== "") {
        const num = parseFloat(rkRaw);
        if (!isNaN(num) && num >= 0 && num <= 100) {
          rk = num;
          modeData.rk = rk;
        } else {
          modeData.rk = "";
        }
      } else {
        modeData.rk = "";
      }

      // Итоговый рейтинг Р = (ТУ + РК) / 2
      if (tu !== null && rk !== null) {
        const rating = Math.round(((tu + rk) / 2) * 10) / 10;
        resultValue.textContent = rating;
        const color = app.getScoreColorClass(rating);
        resultValue.className = `text-2xl font-black ${color.text}`;

        if (rating >= 70) {
          resultStatus.textContent = "Отличный темп";
          resultStatus.className = "text-[10px] font-semibold text-emerald-400";
        } else if (rating >= 50) {
          resultStatus.textContent = "Порог сдан";
          resultStatus.className = "text-[10px] font-semibold text-amber-400";
        } else {
          resultStatus.textContent = "Ниже порога 50";
          resultStatus.className = "text-[10px] font-semibold text-rose-400";
        }

        modeData.rating = rating;
        if (currentMode === "r1") {
          if (rdInputR1 && (!rdInputR1.value || rdInputR1.dataset.autoFilled === "true")) {
            rdInputR1.value = rating;
            rdInputR1.dataset.autoFilled = "true";
          }
        } else if (currentMode === "r2") {
          if (rdInputR2 && (!rdInputR2.value || rdInputR2.dataset.autoFilled === "true")) {
            rdInputR2.value = rating;
            rdInputR2.dataset.autoFilled = "true";
          }
        }
      } else if (tu !== null) {
        resultValue.textContent = `${tu}*`;
        resultValue.className = "text-2xl font-black text-slate-300";
        resultStatus.textContent = "Ожидание РК";
        resultStatus.className = "text-[10px] font-semibold text-slate-400";
        modeData.rating = null;
      } else if (rk !== null) {
        resultValue.textContent = `${rk}*`;
        resultValue.className = "text-2xl font-black text-slate-300";
        resultStatus.textContent = "Ожидание ТУ";
        resultStatus.className = "text-[10px] font-semibold text-slate-400";
        modeData.rating = null;
      } else {
        resultValue.textContent = "—";
        resultValue.className = "text-2xl font-black text-white";
        resultStatus.textContent = "Заполните баллы";
        resultStatus.className = "text-[10px] font-semibold text-slate-400";
        modeData.rating = null;
      }
    }

    function calculateAdmission() {
      const r1Val = parseFloat((rdInputR1.value || "").replace(",", "."));
      const r2Val = parseFloat((rdInputR2.value || "").replace(",", "."));

      const hasR1 = !isNaN(r1Val) && r1Val >= 0 && r1Val <= 100;
      const hasR2 = !isNaN(r2Val) && r2Val >= 0 && r2Val <= 100;

      if (hasR1 && hasR2) {
        const rd = Math.round(((r1Val + r2Val) / 2) * 10) / 10;
        rdValue.textContent = rd;
        const color = app.getScoreColorClass(rd);
        rdValue.className = `text-2xl font-black ${color.text}`;

        if (rd >= 50) {
          rdStatus.textContent = "🟢 Допущен к экзамену";
          rdStatus.className = "text-[10px] font-bold text-emerald-400";
        } else {
          rdStatus.textContent = "🔴 Не допущен к экзамену";
          rdStatus.className = "text-[10px] font-bold text-rose-400";
        }

        renderExamForecast(rd);
      } else {
        rdValue.textContent = "—";
        rdValue.className = "text-2xl font-black text-white";
        rdStatus.textContent = "Введите Р1 и Р2";
        rdStatus.className = "text-[10px] font-semibold text-slate-400";
        if (examTargets) {
          examTargets.innerHTML = `<div class="col-span-3 text-slate-500 text-[11px] py-1">Для прогноза введите оба рейтинга (Р1 и Р2)</div>`;
        }
      }
    }

    function renderExamForecast(rd) {
      if (!examTargets) return;
      const targets = [
        { grade: "Сдача (50)", target: 50 },
        { grade: "Хорошо (70)", target: 70 },
        { grade: "Отлично (90)", target: 90 },
      ];

      examTargets.innerHTML = targets.map(t => {
        const needed = Math.round(((t.target - rd * 0.6) / 0.4) * 10) / 10;
        let badgeColor = "text-emerald-400";
        let displayScore = `${needed} б.`;

        if (needed <= 0) {
          displayScore = "✓ Сдано";
          badgeColor = "text-emerald-400";
        } else if (needed > 100) {
          displayScore = "Нереально";
          badgeColor = "text-rose-400";
        } else if (needed > 75) {
          badgeColor = "text-amber-400";
        }

        return `
          <div class="p-2 rounded-xl bg-slate-800/70 border border-slate-700/60 text-center">
            <div class="text-[10px] text-slate-400 truncate">${t.grade}</div>
            <div class="text-xs font-bold ${badgeColor} mt-0.5">${displayScore}</div>
          </div>
        `;
      }).join("");
    }

    function switchMode(newMode) {
      currentMode = newMode;
      app.triggerHaptic("light");

      const buttons = [tabR1, tabR2, tabRd];
      buttons.forEach(b => {
        b.className = "flex-1 py-1.5 font-semibold rounded-lg transition-all text-slate-400 hover:text-white";
      });

      if (newMode === "r1") {
        tabR1.className = "flex-1 py-1.5 font-semibold rounded-lg transition-all bg-emerald-500 text-white shadow-sm";
        formulaText.textContent = "P1 = (ТУ1 + РК1) / 2";
        rkLabel.textContent = "РК1 (рубеж):";
        resultLabel.textContent = "Итоговый рейтинг Р1:";
        resultSubtext.textContent = "P1 = (ТУ1 + РК1) / 2";
        ratingSection.classList.remove("hidden");
        rdSection.classList.add("hidden");

        rkInput.value = memory.r1.rk !== "" && memory.r1.rk !== null ? memory.r1.rk : "";
        renderWeekCells();
        calculateRating();
      } else if (newMode === "r2") {
        tabR2.className = "flex-1 py-1.5 font-semibold rounded-lg transition-all bg-emerald-500 text-white shadow-sm";
        formulaText.textContent = "P2 = (ТУ2 + РК2) / 2";
        rkLabel.textContent = "РК2 (рубеж):";
        resultLabel.textContent = "Итоговый рейтинг Р2:";
        resultSubtext.textContent = "P2 = (ТУ2 + РК2) / 2";
        ratingSection.classList.remove("hidden");
        rdSection.classList.add("hidden");

        rkInput.value = memory.r2.rk !== "" && memory.r2.rk !== null ? memory.r2.rk : "";
        renderWeekCells();
        calculateRating();
      } else if (newMode === "rd") {
        tabRd.className = "flex-1 py-1.5 font-semibold rounded-lg transition-all bg-emerald-500 text-white shadow-sm";
        formulaText.textContent = "РД = (Р1 + Р2) / 2 • Порог ≥ 50";
        ratingSection.classList.add("hidden");
        rdSection.classList.remove("hidden");

        if (memory.r1.rating !== null && !rdInputR1.value) {
          rdInputR1.value = memory.r1.rating;
          rdInputR1.dataset.autoFilled = "true";
        }
        if (memory.r2.rating !== null && !rdInputR2.value) {
          rdInputR2.value = memory.r2.rating;
          rdInputR2.dataset.autoFilled = "true";
        }

        calculateAdmission();
      }
    }

    tabR1.addEventListener("click", () => switchMode("r1"));
    tabR2.addEventListener("click", () => switchMode("r2"));
    tabRd.addEventListener("click", () => switchMode("rd"));

    rkInput.addEventListener("input", () => {
      calculateRating();
    });
    rkInput.addEventListener("focus", () => {
      rkInput.select();
    });

    if (rdInputR1) {
      rdInputR1.addEventListener("input", () => {
        delete rdInputR1.dataset.autoFilled;
        calculateAdmission();
      });
      rdInputR1.addEventListener("focus", () => rdInputR1.select());
    }
    if (rdInputR2) {
      rdInputR2.addEventListener("input", () => {
        delete rdInputR2.dataset.autoFilled;
        calculateAdmission();
      });
      rdInputR2.addEventListener("focus", () => rdInputR2.select());
    }

    if (btnReset) {
      btnReset.addEventListener("click", (e) => {
        e.stopPropagation();
        app.triggerHaptic("medium");
        memory.r1 = { lectures: {}, practices: {}, rk: "", rating: null };
        memory.r2 = { lectures: {}, practices: {}, rk: "", rating: null };
        rkInput.value = "";
        if (rdInputR1) { rdInputR1.value = ""; delete rdInputR1.dataset.autoFilled; }
        if (rdInputR2) { rdInputR2.value = ""; delete rdInputR2.dataset.autoFilled; }
        if (currentMode === "rd") {
          calculateAdmission();
        } else {
          renderWeekCells();
          calculateRating();
        }
      });
    }

    app.calculator.fillFromCourse = function (course, part) {
      const targetMode = part === 1 ? "r1" : "r2";
      switchMode(targetMode);

      const p = part === 1 ? course.part1 : course.part2;
      const weeksList = getWeeksList(targetMode);

      memory[targetMode].lectures = {};
      memory[targetMode].practices = {};

      (p?.activities || []).forEach(act => {
        const typeLower = (act.type || "").toLowerCase();
        const isLecture = typeLower.includes("лекц") || typeLower.includes("lec");
        const targetField = isLecture ? "lectures" : "practices";

        (act.weeks || []).forEach(w => {
          const weekNum = parseInt(w.week, 10);
          const val = parseFloat(String(w.val).replace(",", "."));
          if (!isNaN(weekNum) && weeksList.includes(weekNum) && !isNaN(val) && val > 0 && val <= 100) {
            memory[targetMode][targetField][weekNum] = val;
          }
        });
      });

      const rkNum = parseFloat(String(p?.rk).replace(",", "."));
      if (!isNaN(rkNum) && rkNum >= 0 && rkNum <= 100) {
        memory[targetMode].rk = rkNum;
        rkInput.value = rkNum;
      } else {
        memory[targetMode].rk = "";
        rkInput.value = "";
      }

      renderWeekCells();
      calculateRating();
      setCollapsed(false);

      const calcCard = document.getElementById("gradeCalculatorCard");
      if (calcCard) {
        calcCard.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    };

    renderWeekCells();
    calculateRating();
  };

})(window.TouApp);
