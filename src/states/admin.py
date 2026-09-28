from aiogram.fsm.state import StatesGroup, State


class AdminState(StatesGroup):
    waiting_for_broadcast_msg = State()
