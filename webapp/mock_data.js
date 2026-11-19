/**
 * Фолбэк-данные для локального тестирования в обычном браузере
 * (когда приложение запущено вне Telegram или пока нет подключения к порталу).
 */
window.MOCK_DATA = {
  student: {
    name: "Демо Студент",
    login: "demo_student",
    status_overall: "В норме",
    current_week: 9,
    is_demo: true,
    is_offline: false
  },
  live_widget: {
    status: "in_lesson", // in_lesson, break, before_day, after_day, weekend
    lesson_number: 1,
    bell_slot_number: 3,
    start: "10:15",
    end: "11:05",
    subject: "Объектно-ориентированное программирование (Java)",
    type: "пр./сем.",
    room: "А-406",
    teacher: "Айтбаева К. Ж.",
    remaining_minutes: 24,
    break_duration: 10,
    next_subject: "Объектно-ориентированное программирование (Java)",
    next_room: "А-406"
  },
  schedule: {
    "Понедельник": [
      { number: 1, time: "08:15-09:05", subject: "Архитектура компьютерных систем", type: "лек.", room: "А-7", teacher: "ст.преп. Самуратов А.Т." },
      { number: 2, time: "09:15-10:05", subject: "Архитектура компьютерных систем", type: "пр.", room: "А-308", teacher: "ст.преп. Самуратов А.Т." },
      { number: 3, time: "10:15-11:05", subject: "Иностранный язык (профессиональный)", type: "пр.", room: "Б-105", teacher: "доц. Смагулова Г.К." }
    ],
    "Вторник": [
      { number: 1, time: "10:15-11:05", subject: "Объектно-ориентированное программирование (Java)", type: "пр./сем.", room: "А-406", teacher: "Айтбаева К. Ж." },
      { number: 2, time: "11:15-12:05", subject: "Объектно-ориентированное программирование (Java)", type: "пр./сем.", room: "А-406", teacher: "Айтбаева К. Ж." },
      { number: 3, time: "12:35-13:25", subject: "Системы управления базами данных", type: "пр./сем.", room: "А-404", teacher: "Айтбаева К. Ж." },
      { number: 4, time: "13:35-14:25", subject: "Системы управления базами данных", type: "лаб.", room: "А-404", teacher: "Айтбаева К. Ж." }
    ],
    "Среда": [
      { number: 1, time: "08:15-09:05", subject: "Алгоритмы и структуры данных", type: "лек.", room: "А-9", teacher: "доц. Ахметов Т.С." },
      { number: 2, time: "09:15-10:05", subject: "Алгоритмы и структуры данных", type: "пр.", room: "А-315", teacher: "преп. Касимова А.А." },
      { number: 3, time: "10:15-11:05", subject: "Web-разработка и фреймворки", type: "лек.", room: "А-7", teacher: "преп. Муратов Е.Е." }
    ],
    "Четверг": [
      { number: 1, time: "09:15-10:05", subject: "Компьютерные сети", type: "лек.", room: "А-7", teacher: "ст.преп. Самуратов А.Т." },
      { number: 2, time: "10:15-11:05", subject: "Компьютерные сети", type: "лаб.", room: "Б-204", teacher: "Сейткалиев М.Б." },
      { number: 3, time: "11:15-12:05", subject: "Операционные системы", type: "пр.", room: "А-410", teacher: "преп. Оспанов Д.К." }
    ],
    "Пятница": [
      { number: 1, time: "10:15-11:05", subject: "Веб-технологии", type: "лек.", room: "А-7", teacher: "преп. Муратов Е.Е." },
      { number: 2, time: "11:15-12:05", subject: "Веб-технологии", type: "лаб.", room: "А-318", teacher: "преп. Муратов Е.Е." }
    ]
  },
  grades: {
    current_part: 2,
    current_week: 9,
    courses: [
      {
        title: "Компьютерные сети",
        teachers: [{ type: "Лекция", fio: "Самуратов А. Т." }, { type: "Практика", fio: "Сейткалиев М. Б." }],
        part1: {
          tu: "84.5",
          rk: "85",
          rating: "85",
          traffic: "🟢",
          activities: [
            { type: "Лекции", avg: "88", weeks: [{ week: 1, val: "90" }, { week: 2, val: "85" }, { week: 3, val: "90" }, { week: 5, val: "87" }] },
            { type: "Практика", avg: "82", weeks: [{ week: 1, val: "80" }, { week: 2, val: "85" }, { week: 3, val: "80" }, { week: 6, val: "83" }] }
          ]
        },
        part2: {
          tu: "90.0",
          rk: "—",
          rating: "—",
          traffic: "🟢",
          activities: [
            { type: "Лекции", avg: "95", weeks: [{ week: 9, val: "95" }] },
            { type: "Практика", avg: "85", weeks: [{ week: 9, val: "85" }] }
          ]
        }
      },
      {
        title: "Базы данных",
        teachers: [{ type: "Лабораторные", fio: "Жумадилов А. К." }],
        part1: {
          tu: "72.0",
          rk: "70",
          rating: "71",
          traffic: "🟢",
          activities: [
            { type: "Лабораторные", avg: "72", weeks: [{ week: 1, val: "75" }, { week: 2, val: "70" }, { week: 4, val: "71" }] }
          ]
        },
        part2: {
          tu: "65.0",
          rk: "—",
          rating: "—",
          traffic: "🟠",
          activities: [
            { type: "Лабораторные", avg: "65", weeks: [{ week: 9, val: "65" }] }
          ]
        }
      },
      {
        title: "Операционные системы",
        teachers: [{ type: "Лекция", fio: "Исаев Б. М." }],
        part1: {
          tu: "92.0",
          rk: "95",
          rating: "94",
          traffic: "🟢",
          activities: [
            { type: "Лекции", avg: "92", weeks: [{ week: 1, val: "95" }, { week: 3, val: "90" }, { week: 5, val: "91" }] }
          ]
        },
        part2: {
          tu: "95.0",
          rk: "—",
          rating: "—",
          traffic: "🟢",
          activities: [
            { type: "Лекции", avg: "95", weeks: [{ week: 9, val: "95" }] }
          ]
        }
      }
    ]
  },
  status_checks: [
    { name: "Допуск к экзаменам", value: "Допущен", indicator: "positive" },
    { name: "Текущая успеваемость", value: "В норме (выше 50)", indicator: "positive" },
    { name: "Задолженности", value: "Отсутствуют", indicator: "positive" },
    { name: "Флюорография", value: "до 25.12.2026", indicator: "positive" }
  ],
  key_dates: [
    { title: "Учебный период (осенний)", period: "01.09.2026 - 12.12.2026", status: "осталось 43 дня", marker: "🔵" },
    { title: "РК №1", period: "12.10.2026 - 24.10.2026", status: "завершено", marker: "✅" },
    { title: "РК №2", period: "30.11.2026 - 12.12.2026", status: "начнётся через 31 день", marker: "🔹" },
    { title: "1-я зимняя сессия", period: "14.12.2026 - 02.01.2027", status: "начнётся через 45 дней", marker: "🔹" },
    { title: "Зимние каникулы", period: "04.01.2027 - 16.01.2027", status: "начнётся через 66 дней", marker: "🔹" }
  ]
};
