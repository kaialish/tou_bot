import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

sys.path.insert(0, os.path.abspath("."))

from src.config import LESSONS_SCHEDULE
from src.services.scheduler import (
    is_mook_lesson,
    _format_user_notification,
    _matches_lesson_slot,
    _get_user_slots_today,
    _sent_user_notifications,
    send_notification_task,
)
from src.services.parser import parse_schedule_items


class TestMookDetection(unittest.TestCase):
    def test_mook_detection_cyrillic(self):
        """Проверка кириллических маркеров МООК."""
        self.assertTrue(is_mook_lesson({"room": "МООК-1", "subject": "Финансы", "type": "лек."}))
        self.assertTrue(is_mook_lesson({"room": "МООК-2", "subject": "Финансы", "type": "пр."}))
        self.assertTrue(is_mook_lesson({"room": "МООК", "subject": "Финансы", "type": "лек."}))
        self.assertTrue(is_mook_lesson({"room": "Дистанционно", "subject": "История", "type": "лек."}))
        self.assertTrue(is_mook_lesson({"room": "", "subject": "Основы МООК", "type": "лек."}))
        self.assertTrue(is_mook_lesson({"room": "СДО", "subject": "Экономика", "type": "лек."}))
        self.assertTrue(is_mook_lesson({"room": "Онлайн", "subject": "Философия", "type": "дистанц. лек."}))

    def test_mook_detection_latin(self):
        """Проверка латинских маркеров MOOK / MOOC / online."""
        self.assertTrue(is_mook_lesson({"room": "MOOK-1", "subject": "Finance", "type": "lec."}))
        self.assertTrue(is_mook_lesson({"room": "MOOC", "subject": "AI", "type": "lec."}))
        self.assertTrue(is_mook_lesson({"room": "Online", "subject": "Math", "type": "seminar"}))
        self.assertTrue(is_mook_lesson({"room": "Zoom", "subject": "Physics", "type": "lec."}))
        self.assertTrue(is_mook_lesson({"room": "Teams", "subject": "English", "type": "lec."}))

    def test_regular_in_person_lessons(self):
        """Обычные очные пары не должны определяться как МООК."""
        self.assertFalse(is_mook_lesson({"room": "А-404", "subject": "Технология программирования", "type": "пр./сем."}))
        self.assertFalse(is_mook_lesson({"room": "А-401", "subject": "Программирование на Python", "type": "пр./сем."}))
        self.assertFalse(is_mook_lesson({"room": "Б-215", "subject": "Базы данных", "type": "лек."}))
        self.assertFalse(is_mook_lesson({"room": "Г-100", "subject": "Физкультура", "type": "практ."}))


class TestNotificationFormatting(unittest.TestCase):
    def setUp(self):
        with open('debug_schedule.html', 'r', encoding='utf-8') as f:
            html = f.read()
        target = datetime(2026, 11, 13)
        self.today_lessons = parse_schedule_items(html, day='today', target_date=target)
        self.user_slots = _get_user_slots_today(self.today_lessons)

    def test_slots_count(self):
        """Проверяем, что пятничное расписание корректно сопоставлено со слотами."""
        slot_numbers = [s["number"] for s, _ in self.user_slots]
        print(f"\n[TEST] Пятничные слоты пользователя: {slot_numbers}", flush=True)
        # Слоты 8, 9, 10 (очные) и 11, 12, 13 (МООК)
        self.assertIn(8, slot_numbers)
        self.assertIn(9, slot_numbers)
        self.assertIn(10, slot_numbers)
        self.assertIn(11, slot_numbers)
        self.assertIn(12, slot_numbers)
        self.assertIn(13, slot_numbers)

    def test_last_in_person_notification_when_mook_disabled(self):
        """
        Когда у пользователя выключены уведомления МООК (notify_mook=False),
        при окончании 10-й пары (последней очной в А-401)
        бот должен поздравить с окончанием очных пар и упомянуть MOOK!
        """
        slot_10, lesson_10 = next((s, it) for s, it in self.user_slots if s["number"] == 10)
        msg = _format_user_notification(slot_10, lesson_10, self.user_slots, notify_mook=False)
        print("\n--- [TEST] Уведомление на 10-й паре (notify_mook=False) ---", flush=True)
        print(msg, flush=True)
        print("----------------------------------------------------------", flush=True)

        self.assertIn("До окончания 10-й пары осталось 5 минут!", msg)
        self.assertIn("Программирование на Python", msg)
        self.assertIn("Ауд. А-401", msg)
        self.assertIn("последняя очная пара на сегодня", msg)
        self.assertIn("дистанционные занятия МООК", msg)
        self.assertNotIn("Следующая пара:", msg)

    def test_in_person_notification_when_mook_enabled(self):
        """
        Когда у пользователя включены уведомления МООК (notify_mook=True),
        при окончании 10-й пары бот должен указать МООК как следующую пару.
        """
        slot_10, lesson_10 = next((s, it) for s, it in self.user_slots if s["number"] == 10)
        msg = _format_user_notification(slot_10, lesson_10, self.user_slots, notify_mook=True)
        print("\n--- [TEST] Уведомление на 10-й паре (notify_mook=True) ---", flush=True)
        print(msg, flush=True)
        print("---------------------------------------------------------", flush=True)

        self.assertIn("До окончания 10-й пары осталось 5 минут!", msg)
        self.assertIn("Следующая пара: <b>Основы финансовой грамотности</b>", msg)
        self.assertIn("МООК-1 (дистанционно)", msg)
        self.assertNotIn("последняя очная пара", msg)

    def test_mook_notification_when_mook_enabled(self):
        """
        Когда уведомления МООК включены, сообщение о самой МООК паре
        должно показывать значок 🌐 и пометку (дистанционно).
        """
        slot_11, lesson_11 = next((s, it) for s, it in self.user_slots if s["number"] == 11)
        msg = _format_user_notification(slot_11, lesson_11, self.user_slots, notify_mook=True)
        print("\n--- [TEST] Уведомление на 11-й паре МООК (notify_mook=True) ---", flush=True)
        print(msg, flush=True)
        print("--------------------------------------------------------------", flush=True)

        self.assertIn("До окончания 11-й пары осталось 5 минут!", msg)
        self.assertIn("🌐 МООК-1 (дистанционно)", msg)


class TestSchedulerSimulation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        _sent_user_notifications.clear()
        with open('debug_schedule.html', 'r', encoding='utf-8') as f:
            self.html = f.read()

    async def test_scheduler_simulation_mook_disabled(self):
        """
        Симуляция дня для пользователя с notify_mook = 0:
        - 18:05 (конец 10 пары): получает сообщение о завершении очных пар.
        - 19:00 (конец 11 пары МООК): уведомление НЕ отправляется (0 вызовов).
        - 19:55 (конец 12 пары МООК): уведомление НЕ отправляется (0 вызовов).
        - 21:00 (конец 13 пары МООК): уведомление НЕ отправляется (0 вызовов).
        """
        user_id = 820163465
        notify_mook = 0
        last_msg_id = None

        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=999))
        mock_bot.delete_message = AsyncMock()

        # 1. 18:05: конец 10-й очной пары (17:20 - 18:10)
        time_18_05 = datetime(2026, 11, 13, 18, 5, 0)
        with patch("src.services.scheduler._get_now", return_value=time_18_05), \
             patch("src.services.scheduler.set_last_notification_msg_id", new_callable=AsyncMock), \
             patch("src.services.scheduler.get_subscribed_users_with_schedules",
                   new_callable=AsyncMock,
                   return_value=[(user_id, self.html, notify_mook, last_msg_id)]):
            await send_notification_task(mock_bot)

        self.assertEqual(mock_bot.send_message.call_count, 1)
        sent_call = mock_bot.send_message.call_args
        sent_text = sent_call.kwargs["text"]
        print("\n[SIMULATION] Отправлено сообщение в 18:05:", flush=True)
        print(sent_text, flush=True)
        self.assertIn("До окончания 10-й пары осталось 5 минут!", sent_text)
        self.assertIn("последняя очная пара на сегодня", sent_text)

        # 2. 19:00: конец 11-й пары МООК (18:15 - 19:05)
        mock_bot.send_message.reset_mock()
        time_19_00 = datetime(2026, 11, 13, 19, 0, 0)
        with patch("src.services.scheduler._get_now", return_value=time_19_00), \
             patch("src.services.scheduler.set_last_notification_msg_id", new_callable=AsyncMock), \
             patch("src.services.scheduler.get_subscribed_users_with_schedules",
                   new_callable=AsyncMock,
                   return_value=[(user_id, self.html, notify_mook, 999)]):
            await send_notification_task(mock_bot)

        # ДОЛЖНО БЫТЬ 0 ВЫЗОВОВ! МООК заблокирован!
        self.assertEqual(mock_bot.send_message.call_count, 0)
        print("✅ [SIMULATION] 19:00 (МООК-1): Уведомление успешно заблокировано!", flush=True)

        # 3. 19:55: конец 12-й пары МООК (19:10 - 20:00)
        mock_bot.send_message.reset_mock()
        time_19_55 = datetime(2026, 11, 13, 19, 55, 0)
        with patch("src.services.scheduler._get_now", return_value=time_19_55), \
             patch("src.services.scheduler.set_last_notification_msg_id", new_callable=AsyncMock), \
             patch("src.services.scheduler.get_subscribed_users_with_schedules",
                   new_callable=AsyncMock,
                   return_value=[(user_id, self.html, notify_mook, 999)]):
            await send_notification_task(mock_bot)

        self.assertEqual(mock_bot.send_message.call_count, 0)
        print("✅ [SIMULATION] 19:55 (МООК-1): Уведомление успешно заблокировано!", flush=True)

        # 4. 21:00: конец 13-й пары МООК (20:15 - 21:05)
        mock_bot.send_message.reset_mock()
        time_21_00 = datetime(2026, 11, 13, 21, 0, 0)
        with patch("src.services.scheduler._get_now", return_value=time_21_00), \
             patch("src.services.scheduler.set_last_notification_msg_id", new_callable=AsyncMock), \
             patch("src.services.scheduler.get_subscribed_users_with_schedules",
                   new_callable=AsyncMock,
                   return_value=[(user_id, self.html, notify_mook, 999)]):
            await send_notification_task(mock_bot)

        self.assertEqual(mock_bot.send_message.call_count, 0)
        print("✅ [SIMULATION] 21:00 (МООК-1): Уведомление успешно заблокировано!", flush=True)

    async def test_scheduler_simulation_mook_enabled(self):
        """
        Симуляция для пользователя с notify_mook = 1:
        - 19:00 (конец 11 пары МООК): уведомление отправляется.
        """
        user_id = 820163465
        notify_mook = 1
        last_msg_id = None

        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=1001))
        mock_bot.delete_message = AsyncMock()

        time_19_00 = datetime(2026, 11, 13, 19, 0, 0)
        with patch("src.services.scheduler._get_now", return_value=time_19_00), \
             patch("src.services.scheduler.set_last_notification_msg_id", new_callable=AsyncMock), \
             patch("src.services.scheduler.get_subscribed_users_with_schedules",
                   new_callable=AsyncMock,
                   return_value=[(user_id, self.html, notify_mook, last_msg_id)]):
            await send_notification_task(mock_bot)

        self.assertEqual(mock_bot.send_message.call_count, 1)
        sent_call = mock_bot.send_message.call_args
        sent_text = sent_call.kwargs["text"]
        print("\n[SIMULATION] Отправлено сообщение в 19:00 при включенном MOOK:", flush=True)
        print(sent_text, flush=True)
        self.assertIn("До окончания 11-й пары осталось 5 минут!", sent_text)
        self.assertIn("🌐 МООК-1 (дистанционно)", sent_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
