import logging

from aiogram.fsm.state import State

logger = logging.getLogger(__name__)


class StateHistory:
    def __init__(self, lst: list[State] | None = None):
        self._lst: list[State] = lst if lst else []
        logger.debug("Load %s", self)

    def __len__(self):
        return len(self._lst)

    def __bool__(self):
        return bool(self._lst)

    def __getitem__(self, item):
        return self._lst[item]

    def __repr__(self):
        return f"History({self._lst})"

    def __iter__(self):
        return iter(self._lst)

    def append(self, value: State) -> None:
        if self._lst:
            if self._lst[-1] != value:
                self._lst.append(value)
        else:
            self._lst.append(value)
        logger.debug("History.append value=%s %s", value, self)

    def back(self) -> State | None:
        return self._lst[-1] if self._lst else None

    def pop(self) -> State | None:
        value = self._lst.pop() if self._lst else None
        logger.debug("History.pop value=%s %s", value, self)
        return value

    def as_list(self) -> list[str]:
        return [s.state for s in self._lst]

    @classmethod
    def from_list(cls, values: list[str]) -> "StateHistory":
        states = []
        for raw in values:
            if ":" in raw:
                *group_parts, state_name = raw.split(":")
                group_name = ":".join(group_parts)
                states.append(State(state=state_name, group_name=group_name))
            else:
                states.append(State(state=raw))
        return StateHistory(states)
