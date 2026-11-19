// Симулируем функцию рендеринга и подсветки пар из app.js
const lessons = [
  { number: 1, time: "10:15–11:05", subject: "Объектно-ориентированное программирование (Java)", room: "А-406", teacher: "Айтбаева К. Ж." },
  { number: 2, time: "11:15–12:05", subject: "Объектно-ориентированное программирование (Java)", room: "А-406", teacher: "Айтбаева К. Ж." },
  { number: 3, time: "12:35–13:25", subject: "Системы управления базами данных", room: "А-404", teacher: "Айтбаева К. Ж." },
  { number: 4, time: "13:35–14:25", subject: "Системы управления базами данных", room: "А-404", teacher: "Айтбаева К. Ж." },
  { number: 5, time: "14:35–15:25", subject: "Сетевые технологии", room: "А-308", teacher: "Самуратов А.Т." },
  { number: 6, time: "15:35–16:25", subject: "Сетевые технологии", room: "А-308", teacher: "Самуратов А.Т." }
];

// live_widget полученный от бэкенда
const live = {
  status: "in_lesson",
  lesson_number: 1,
  bell_slot_number: 3,
  start: "10:15",
  end: "11:05",
  subject: "Объектно-ориентированное программирование (Java)"
};

// Время со скриншота: 11:04
const nowMinutes = 11 * 60 + 4; // 664 мин
const isActuallyToday = true;

// Логика из обновлённого app.js:
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

  // 2. Резервная сверка
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

console.log("Found activeLessonNumber:", activeLessonNumber);

const highlighted = [];
lessons.forEach((l) => {
  const isCurrent = (activeLessonNumber !== null) && (l.number === activeLessonNumber);
  if (isCurrent) {
    highlighted.push(l);
  }
});

console.log("Highlighted lessons count:", highlighted.length);
console.log("Highlighted lesson:", highlighted[0]);

if (highlighted.length === 1 && highlighted[0].number === 1) {
  console.log("SUCCESS! Exactly ONE lesson (#1 Java 10:15–11:05) is highlighted!");
} else {
  console.error("FAIL! Highlighted count is not 1 or wrong lesson:", highlighted);
  process.exit(1);
}

