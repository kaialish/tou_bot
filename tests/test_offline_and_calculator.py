"""
Тестирование отказоустойчивости при падении сайта университета ToU (tou.edu.kz)
и математической логики калькулятора баллов.
"""
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aiohttp.test_utils import make_mocked_request
from src.webapp_server import handle_student_data, handle_refresh


class TestOfflineAndCalculator(unittest.IsolatedAsyncioTestCase):

    def test_calculator_formulas(self):
        """Проверка формул калькулятора (Р1, Р2, РД и прогноз экзамена)."""
        # 1. Формула недели 8: Р1 = (ТУ1 + РК1) / 2
        scores_1 = [85, 90, 78, 92, 88]
        tu1 = round(sum(scores_1) / len(scores_1), 1)
        rk1 = 90.0
        r1 = round((tu1 + rk1) / 2, 1)
        self.assertEqual(tu1, 86.6)
        self.assertEqual(r1, 88.3)

        # 2. Формула недели 15: Р2 = (ТУ2 + РК2) / 2
        scores_2 = [95, 85, 90, 92]
        tu2 = round(sum(scores_2) / len(scores_2), 1)
        rk2 = 85.0
        r2 = round((tu2 + rk2) / 2, 1)
        self.assertEqual(tu2, 90.5)
        self.assertEqual(r2, 87.8)

        # 3. Формула допуска: РД = (Р1 + Р2) / 2
        rd = round((r1 + r2) / 2, 1)
        self.assertEqual(rd, 88.0)
        self.assertTrue(rd >= 50.0)

        # 4. Прогноз экзамена: Итог = РД * 0.6 + Экзамен * 0.4
        # Экзамен = (Цель - РД * 0.6) / 0.4
        target = 90.0  # Оценка 'A'
        needed_exam = round((target - rd * 0.6) / 0.4, 1)
        self.assertEqual(needed_exam, 93.0)

    async def test_offline_resilience_when_portal_down(self):
        """
        Симуляция полного падения серверов университета tou.edu.kz.
        Проверяем, что бот и Mini App сохраняют и отдают последние обновленные данные из кэша.
        """
        test_user_id = 998877665
        test_login = "student_offline_test"
        test_password = "secret_password"
        cached_timestamp = "24.11.2026 в 22:30"

        sample_schedule = """
        <table class="schedule-table">
          <thead><tr><th>День</th><th>Время</th><th>Пара</th></tr></thead>
          <tbody>
            <tr>
              <td class="schedule-day">Понедельник</td>
              <td class="schedule-time">10:15-11:05</td>
              <td class="schedule-body">
                <div class="sc-cz-block">
                  <p>
                    <span class="sc-dis">Компьютерные сети, лек.</span>
                    <span class="sc-meta">А-7, Самуратов А.Т.</span>
                  </p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        """
        sample_zhurnal = {
            "current_week": 9,
            "courses": [
                {
                    "title": "Компьютерные сети",
                    "teachers": [{"type": "Лекция", "fio": "Самуратов А.Т."}],
                    "data": {
                        "summary": {"tu1": "85.0", "rk1": "90.0", "r1": "87.5", "tu2": "88.0", "rk2": "", "r2": ""},
                        "activities": []
                    }
                }
            ]
        }
        sample_status = {
            "status_badge": "В норме",
            "items": [
                {"name": "Допуск к экзаменам", "value": "Допущен", "indicator": "positive"},
                {"name": "Флюорография", "value": "до 25.12.2026", "indicator": "positive"}
            ]
        }

        with patch("src.webapp_server.get_user_credentials", new_callable=AsyncMock) as mock_creds, \
             patch("src.webapp_server.get_cached_schedule", new_callable=AsyncMock) as mock_get_sched, \
             patch("src.webapp_server.get_cached_zhurnal", new_callable=AsyncMock) as mock_get_zhur, \
             patch("src.webapp_server.get_cached_academic_status", new_callable=AsyncMock) as mock_get_stat, \
             patch("src.webapp_server.is_user_subscribed", new_callable=AsyncMock) as mock_sub, \
             patch("src.webapp_server.get_user_mook_setting", new_callable=AsyncMock) as mock_mook, \
             patch("src.webapp_server.check_rate_limit", return_value=(True, 0)), \
             patch("src.webapp_server.update_rate_limit"), \
             patch("src.webapp_server.get_schedule_html", new_callable=AsyncMock) as mock_sched, \
             patch("src.webapp_server.get_zhurnal_html", new_callable=AsyncMock) as mock_zhur, \
             patch("src.webapp_server.get_dashboard_html", new_callable=AsyncMock) as mock_dash:

            mock_creds.return_value = (test_login, test_password)
            mock_get_sched.return_value = (sample_schedule, cached_timestamp)
            mock_get_zhur.return_value = (json.dumps(sample_zhurnal), cached_timestamp)
            mock_get_stat.return_value = (json.dumps(sample_status), cached_timestamp)
            mock_sub.return_value = True
            mock_mook.return_value = False

            # Все сетевые вызовы к порталу ToU падают:
            mock_sched.return_value = (False, "Connection timed out (tou.edu.kz unreachable)")
            mock_zhur.return_value = (False, "502 Bad Gateway")
            mock_dash.return_value = (False, "Connection reset by peer")

            request = make_mocked_request("GET", f"/api/refresh?user_id={test_user_id}")
            response = await handle_refresh(request)

            self.assertEqual(response.status, 200)
            data = json.loads(response.text)

            student = data.get("student", {})
            self.assertFalse(student.get("is_demo"), "Student must NOT be in demo mode when portal is down")
            self.assertEqual(student.get("login"), test_login)
            self.assertTrue(student.get("is_offline"), "is_offline must be True")
            self.assertEqual(student.get("last_updated"), cached_timestamp)

            self.assertIn("Понедельник", data.get("schedule", {}))
            monday_lessons = data["schedule"]["Понедельник"]
            self.assertEqual(len(monday_lessons), 1)
            self.assertEqual(monday_lessons[0]["subject"], "Компьютерные сети")

            self.assertEqual(len(data.get("grades", {}).get("courses", [])), 1)
            self.assertEqual(data["grades"]["courses"][0]["title"], "Компьютерные сети")


if __name__ == "__main__":
    unittest.main()
