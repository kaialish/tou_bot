from aiogram.fsm.state import StatesGroup, State


class AuthForm(StatesGroup):
    waiting_for_disclaimer_accept = State()
    waiting_for_login = State()
    waiting_for_password = State()
    authorized = State()
