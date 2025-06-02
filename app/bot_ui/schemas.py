from pydantic import BaseModel, Field

from .bot_types import StateHistory


class StateData(BaseModel):
    keyboard_id: int | None = None
    history: StateHistory = Field(default_factory=StateHistory)

    channels_menu_offset: int = 0
    telegrams_menu_offset: int = 0
    categories_menu_offset: int = 0

    chat_id: int | None = None
    thread_id: int | None = None

    channel_id: int | None = None

    selected_categories: set[int] = Field(default_factory=set)
