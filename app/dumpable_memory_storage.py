import pickle

from aiogram.fsm.storage.memory import MemoryStorage


class DumpableMemoryStorage(MemoryStorage):
    def __init__(self, file_name: str):
        super().__init__()
        self._file_name = file_name

    def load(self) -> bool:
        try:
            with open(self._file_name, "rb") as file:
                self.storage = pickle.load(file)
                return True
        except (FileNotFoundError, EOFError, TypeError, ValueError):
            return False

    def dump(self) -> None:
        with open(self._file_name, "wb") as file:
            pickle.dump(self.storage, file)

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.dump()


async def example():
    from aiogram import Bot, Dispatcher

    bot = Bot(token="")
    with DumpableMemoryStorage("app_data/storage.pickle") as storage:
        dp = Dispatcher(storage=storage)
        # ...
        await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(example())
