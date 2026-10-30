"""Offline regression tests. No configuration, secrets, database or network are loaded."""
import ast
import copy
from datetime import datetime
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from aiogram.exceptions import TelegramBadRequest

ROOT = Path(__file__).resolve().parents[1]


def load_parser():
    tree = ast.parse((ROOT / "src/services/parser.py").read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom) and node.module == "src.config"
    )]
    namespace = {"get_kz_now": lambda: datetime(2026, 10, 29, 12)}
    exec(compile(tree, "src/services/parser.py", "exec"), namespace)
    return SimpleNamespace(**namespace)


PARSER = load_parser()
KEYBOARDS = {}
exec(compile((ROOT / "src/keyboards/inline.py").read_text(encoding="utf-8"),
             "src/keyboards/inline.py", "exec"), KEYBOARDS)


def journal_html(week):
    def cells(values):
        return "".join(f"<td>{value}</td>" for value in values)

    headers = (
        '<td colspan="9">Лекции</td><td colspan="2">Текущие</td>'
        '<td colspan="2">По ведомости</td><td rowspan="2">Р1</td>'
        '<td colspan="8">Лекции</td><td colspan="2">Текущие</td>'
        '<td colspan="2">По ведомости</td><td rowspan="2">Р2</td>'
    )
    columns = list(range(1, 9)) + ["Сред.", "ТУ1", "РК1", "ТУ1", "РК1"]
    columns += list(range(9, 16)) + ["Сред.", "ТУ2", "РК2", "ТУ2", "РК2"]
    values = [0] + [80] * 8 + [80, 40, 70, 40, 70, 74]
    values += [90] * 7 + [90, 45, 60, 45, 60, 78] + [76, "", "", "", ""]
    return (
        f'<div>Неделя: <b>{week}</b></div>'
        '<section class="student-zhurnal__course">'
        '<div class="student-zhurnal__course-head"><h2>Test course</h2></div>'
        f'<table><tr><td>Header</td></tr><tr>{headers}</tr>'
        f'<tr>{cells(columns)}</tr><tr>{cells(values)}</tr></table></section>'
    )


def journal(week=9):
    return PARSER.parse_zhurnal(journal_html(week))


class GradeCalculationTests(unittest.TestCase):
    def test_parser_keeps_both_parts_and_summaries(self):
        data = journal()["courses"][0]["data"]
        self.assertEqual([g["week"] for g in data["activities"][0]["r1_grades"]],
                         [str(w) for w in range(1, 9)])
        self.assertEqual([g["week"] for g in data["activities"][0]["r2_grades"]],
                         [str(w) for w in range(9, 16)])
        self.assertEqual([data["summary"][k] for k in ("rk1", "r1", "rk2", "r2")],
                         ["70", "74", "60", "78"])

    def test_first_part_is_stable_after_week_eight(self):
        grades = journal()["courses"][0]["data"]["activities"][0]["r1_grades"]
        for week in (8, 9, 15, 16):
            with self.subTest(week=week):
                filtered, avg, has_grades = PARSER._filter_grades_by_current_week(grades, week, 1)
                self.assertEqual(len(filtered), 8)
                self.assertEqual(avg, 80)
                self.assertTrue(has_grades)

    def test_second_part_uses_its_own_week_count(self):
        grades = journal()["courses"][0]["data"]["activities"][0]["r2_grades"]
        for week, count in ((9, 1), (10, 2), (15, 7), (16, 7)):
            with self.subTest(week=week):
                filtered, avg, _ = PARSER._filter_grades_by_current_week(grades, week, 2)
                self.assertEqual(len(filtered), count)
                self.assertEqual(filtered[0]["week"], "9")
                self.assertEqual(avg, 90)

    def test_missing_elapsed_week_counts_as_zero_and_future_is_ignored(self):
        grades = [{"week": "9", "grade": "80,5"}, {"week": "11", "grade": "100"}]
        filtered, avg, _ = PARSER._filter_grades_by_current_week(grades, 10, 2)
        self.assertEqual(filtered, [{"week": "9", "grade": "80,5"}, {"week": "10", "grade": "0"}])
        self.assertEqual(avg, 40.25)

    def test_first_part_before_week_eight_preserves_existing_calculation(self):
        data = journal(7)["courses"][0]["data"]
        self.assertEqual(PARSER._calc_course_real_tu(data["activities"], 7, part=1), (80, True))

    def test_second_part_has_no_average_before_week_nine(self):
        self.assertEqual(PARSER._filter_grades_by_current_week([], 8, 2), ([], None, False))
        self.assertEqual(PARSER._calc_course_real_tu([], 8, fallback_tu="95", part=2), (None, False))
        for text in self.views(journal(8), 2):
            self.assertIn("ещё не началась", text)
            self.assertIn("ТУ2: <b>—</b>", text)
            self.assertNotIn("🔴", text)
            self.assertNotIn("9н:", text)

    def test_activity_from_other_part_does_not_dilute_average(self):
        activities = [
            {"r1_grades": [{"week": "1", "grade": "80"}], "r2_grades": []},
            {"r1_grades": [], "r2_grades": [{"week": "9", "grade": "90"}]},
        ]
        self.assertEqual(PARSER._calc_course_real_tu(activities, 9, part=2), (90, True))

    def test_fallback_is_selected_for_current_part(self):
        data = journal()
        data["courses"][0]["data"]["activities"] = []
        for text in self.views(data, 2):
            self.assertIn("ТУ2: <b>45</b>", text)
            self.assertNotIn("ТУ1:", text)

    def test_brief_and_full_show_only_selected_part(self):
        for part, score, rk, rating in ((1, 80, 70, 74), (2, 90, 60, 78)):
            for text in self.views(journal(), part):
                self.assertIn(f"ТУ{part}: <b>{score}</b>", text)
                self.assertIn(f"РК{part}: <b>{rk}</b>", text)
                self.assertIn(f"Р{part}: <b>{rating}</b>", text)
                self.assertNotIn(f"ТУ{3 - part}:", text)
        full1 = "\n".join(PARSER.format_zhurnal_full_chunks(journal(), part=1))
        full2 = "\n".join(PARSER.format_zhurnal_full_chunks(journal(), part=2))
        self.assertIn("8н: 80", full1)
        self.assertNotIn("9н:", full1)
        self.assertIn("9н: 90", full2)
        self.assertNotIn("1н:", full2)
        self.assertNotIn("10н:", full2)

    def test_default_part_tracks_portal_week_and_supports_old_cache(self):
        self.assertEqual(PARSER.get_zhurnal_part(journal(8)), 1)
        self.assertEqual(PARSER.get_zhurnal_part(journal(9)), 2)
        self.assertIn("ТУ2:", PARSER.format_zhurnal_brief(journal(9)))
        self.assertIn("ТУ1:", PARSER.format_zhurnal_brief(journal(8)))
        self.assertIn("ТУ2:", PARSER.format_zhurnal_brief(journal()["courses"]))

    def test_empty_first_week_of_second_part_is_neutral(self):
        data = journal()
        grades = data["courses"][0]["data"]["activities"][0]["r2_grades"]
        grades[0]["grade"] = ""
        for text in self.views(data, 2):
            self.assertIn("⚪", text)
            self.assertNotIn("🔴", text)
        data["current_week"] = 10
        grades[1]["grade"] = "0"
        for text in self.views(data, 2):
            self.assertIn("🔴", text)

    def test_chunked_full_journal_keeps_part_context(self):
        data = journal()
        data["courses"] = [copy.deepcopy(data["courses"][0]) for _ in range(35)]
        chunks = PARSER.format_zhurnal_full_chunks(data, part=2)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertIn("2-я часть", chunk)
            self.assertLess(len(chunk), 4096)
            self.assertNotIn("ТУ1:", chunk)

    def test_both_buttons_and_selected_marker(self):
        for part in (1, 2):
            for view in ("brief", "full"):
                kb = KEYBOARDS["get_grades_keyboard"](view, part).inline_keyboard
                self.assertEqual([b.callback_data for b in kb[0]], ["grades_part_1", "grades_part_2"])
                self.assertTrue(kb[0][part - 1].text.startswith("✓ "))
                self.assertFalse(kb[0][2 - part].text.startswith("✓ "))

    @staticmethod
    def views(data, part):
        return (PARSER.format_zhurnal_brief(data, part=part),
                "\n".join(PARSER.format_zhurnal_full_chunks(data, part=part)))


class MemoryState:
    def __init__(self, data):
        self.data = data

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **changes):
        self.data.update(changes)


class GradeHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Compile only the real grades functions, bypassing application startup/imports.
        tree = ast.parse((ROOT / "src/handlers/common.py").read_text(encoding="utf-8"))
        nodes = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
                 and ("grades" in node.name)]
        for node in nodes:
            node.decorator_list = []
        ns = {
            "CallbackQuery": object, "FSMContext": object, "json": json,
            "TelegramBadRequest": TelegramBadRequest,
            "get_kz_now": lambda: datetime(2026, 10, 29, 12),
            "get_grades_keyboard": KEYBOARDS["get_grades_keyboard"],
        }
        ns.update({k: v for k, v in vars(PARSER).items() if not k.startswith("__")})
        for name in ("get_user_credentials", "get_zhurnal_html", "get_cached_zhurnal", "save_cached_zhurnal"):
            ns[name] = AsyncMock()
        ns["get_zhurnal_html"].return_value = (True, journal_html(9))
        ns["get_cached_zhurnal"].return_value = None
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "src/handlers/common.py", "exec"), ns)
        self.ns = ns
        self.state = MemoryState({
            "login": "synthetic-user", "password": "synthetic-test-value",
            "cached_zhurnal_json": json.dumps(journal()), "cached_zhurnal_time": "test cache",
        })
        message = SimpleNamespace(
            chat=SimpleNamespace(id=123), message_id=10,
            edit_text=AsyncMock(), delete=AsyncMock(),
            answer=AsyncMock(return_value=SimpleNamespace(message_id=11)),
        )
        self.callback = SimpleNamespace(
            from_user=SimpleNamespace(id=123), message=message,
            bot=SimpleNamespace(delete_message=AsyncMock()), answer=AsyncMock(), data="grades_part_2",
        )

    async def test_unauthorized_callbacks_answer_once_with_login_alert(self):
        self.state.data.pop("login")
        self.state.data.pop("password")
        self.ns["get_user_credentials"].return_value = None
        handlers = ("process_menu_grades", "process_refresh_grades", "process_grades_view_full",
                    "process_grades_view_brief", "process_grades_part")
        for name in handlers:
            with self.subTest(handler=name):
                self.callback.answer.reset_mock()
                await self.ns[name](self.callback, self.state)
                self.callback.answer.assert_awaited_once()
                self.assertTrue(self.callback.answer.call_args.kwargs["show_alert"])
        self.ns["get_zhurnal_html"].assert_not_awaited()
        self.callback.message.edit_text.assert_not_awaited()
        self.callback.message.answer.assert_not_awaited()

    async def test_entry_opens_current_part_from_cache_without_network(self):
        self.state.data["grades_part"] = 1
        await self.ns["process_menu_grades"](self.callback, self.state)
        self.assertEqual(self.state.data["grades_part"], 2)
        self.assertIn("ТУ2:", self.callback.message.edit_text.call_args.args[0])
        self.ns["get_zhurnal_html"].assert_not_awaited()
        self.ns["get_user_credentials"].assert_not_awaited()

    async def test_part_switch_preserves_full_view(self):
        self.state.data.update(grades_part=2, grades_view="full")
        self.callback.data = "grades_part_1"
        await self.ns["process_grades_part"](self.callback, self.state)
        self.assertEqual((self.state.data["grades_part"], self.state.data["grades_view"]), (1, "full"))
        self.assertIn("ТУ1:", self.callback.message.answer.call_args.args[0])
        self.ns["get_zhurnal_html"].assert_not_awaited()

    async def test_view_switches_preserve_part(self):
        self.state.data["grades_part"] = 1
        await self.ns["process_grades_view_full"](self.callback, self.state)
        await self.ns["process_grades_view_brief"](self.callback, self.state)
        self.assertEqual(self.state.data["grades_part"], 1)
        self.assertEqual(self.state.data["grades_view"], "brief")
        self.assertIn("ТУ1:", self.callback.message.edit_text.call_args.args[0])

    async def test_refresh_preserves_full_view_and_first_part(self):
        self.state.data.update(grades_part=1, grades_view="full")
        await self.ns["process_refresh_grades"](self.callback, self.state)
        self.ns["get_zhurnal_html"].assert_awaited_once()
        self.ns["save_cached_zhurnal"].assert_awaited_once()
        self.callback.answer.assert_awaited_once()
        self.assertEqual((self.state.data["grades_part"], self.state.data["grades_view"]), (1, "full"))
        self.assertIn("ТУ1:", self.callback.message.answer.call_args.args[0])

    async def test_offline_refresh_keeps_part_and_uses_database_cache(self):
        self.state.data.update(grades_part=2, grades_view="full")
        self.ns["get_zhurnal_html"].return_value = (False, "Portal unavailable")
        self.ns["get_cached_zhurnal"].return_value = (json.dumps(journal()), "test cache")
        await self.ns["process_refresh_grades"](self.callback, self.state)
        self.assertIn("ТУ2:", self.callback.message.answer.call_args.args[0])
        self.callback.answer.assert_awaited_once()
        self.ns["save_cached_zhurnal"].assert_not_awaited()

    async def test_portal_error_without_cache_keeps_controls(self):
        self.state.data.update(grades_part=2, grades_view="full")
        self.ns["get_zhurnal_html"].return_value = (False, "Portal unavailable")
        await self.ns["process_refresh_grades"](self.callback, self.state)
        call = self.callback.message.edit_text.call_args
        self.assertEqual(call.args[0], "Portal unavailable")
        self.assertTrue(call.kwargs["reply_markup"].inline_keyboard[0][1].text.startswith("✓ "))
        self.callback.answer.assert_awaited_once()

    async def test_full_part_switch_cleans_all_previous_chunks(self):
        self.state.data.update(grades_part=1, grades_view="full", grades_msg_ids=[20, 21, 22])
        await self.ns["process_grades_part"](self.callback, self.state)
        self.assertEqual(self.callback.bot.delete_message.await_count, 3)
        self.assertEqual(self.state.data["grades_msg_ids"], [11])
        self.assertIn("ТУ2:", self.callback.message.answer.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
