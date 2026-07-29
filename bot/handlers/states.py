from aiogram.fsm.state import State, StatesGroup


class AddEvent(StatesGroup):
    title = State()
    date = State()
    time = State()
    custom_time = State()


class EditEvent(StatesGroup):
    title = State()
    date = State()
    time = State()
    custom_time = State()
