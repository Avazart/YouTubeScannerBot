import csv
import sqlite3
from contextlib import closing
from pathlib import Path
from sqlite3 import Cursor


def import_tags(file_path: Path, cursor: Cursor) -> dict[str:int]:
    q = ('INSERT OR REPLACE INTO Tags '
         "(id, name, 'order') "
         'VALUES (?,?,?)')

    tags = {}
    with file_path.open('r', encoding='utf-8', newline='') as file:
        reader = csv.DictReader(file, delimiter=';', quotechar='"', dialect='excel')
        for i, row in enumerate(reader):
            cursor.execute(q, (i + 1, row['name'], row['order']))
            tags[row['name']] = i + 1
    return tags


def import_channels(file_path: Path, tags: dict[str:int], cursor: Cursor) -> dict[str, int]:
    q1 = ('INSERT OR REPLACE INTO YouTubeChannels '
          '(original_id, canonical_base_url, title) '
          'VALUES (?,?,?)')

    q2 = ('INSERT OR REPLACE INTO YouTubeChannelTags '
          "(tag_id, channel_id) "
          'VALUES (?,?)')

    channels = {}
    with file_path.open('r', encoding='utf-8', newline='') as file:
        reader = csv.DictReader(file, delimiter=';', quotechar='"', dialect='excel')
        for row in reader:
            original_id = row['original_id']
            r = cursor.execute(q1, (original_id,
                                    row['canonical_base_url'],
                                    row['title']))
            channel_id = r.lastrowid
            channels[original_id] = channel_id

            for name in map(str.strip, row['tags'].split(',')):
                cursor.execute(q2, (tags[name], channel_id))

    return channels


def import_forwarding(file_path: Path, channels: dict[str:int], cursor: Cursor):
    q1 = ('INSERT OR REPLACE INTO TelegramChats '
          '(original_id, user_name, title) '
          'VALUES (?,?,?)')

    q2 = ('INSERT OR REPLACE INTO TelegramThreads '
          "(original_id, original_chat_id) "
          'VALUES (?,?)')

    q3 = ('INSERT OR REPLACE INTO Forwarding '
          "(youtube_channel_id, telegram_chat_id, telegram_thread_id) "
          'VALUES (?,?,?)')

    with file_path.open('r', encoding='utf-8', newline='') as file:
        reader = csv.DictReader(file, delimiter=';', quotechar='"', dialect='excel')
        for row in reader:
            channel_original_id = row['youtube_channel_id']

            telegram_chat_id = row['telegram_chat_id']
            telegram_chat_title = row['telegram_chat_title']
            telegram_chat_user_name = row['telegram_chat_user_name']

            telegram_thread_id = row['telegram_thread_id']

            r1 = cursor.execute(q1, (telegram_chat_id,
                                     telegram_chat_user_name,
                                     telegram_chat_title))

            if telegram_thread_id is not None:
                r1 = cursor.execute(q2, (telegram_thread_id, telegram_chat_id))
                thread_id = r1.lastrowid
            else:
                thread_id = None

            if channel_id := channels.get(channel_original_id):
                r3 = cursor.execute(q3, (channel_id, telegram_chat_id, thread_id))


def get_all_table_names(cursor: Cursor) -> list[str]:
    q = "SELECT name FROM sqlite_schema " \
        "WHERE type ='table' AND name NOT LIKE 'sqlite_%'"
    return [r[0] for r in cursor.execute(q)]


def get_column_names(cursor: Cursor, table_name: str) -> list[str]:
    q = "SELECT name FROM pragma_table_info(?)"
    c = cursor.execute(q, (table_name,))
    return [r[0] for r in c]


def export_db_to_csv_files(dest_path: Path, cursor: Cursor):
    tables = {}
    table_names = get_all_table_names(cursor)
    for table_name in table_names:
        column_names = get_column_names(cursor, table_name)
        tables[table_name] = column_names

    with (dest_path / 'Tables.csv').open('w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file, delimiter=';', quotechar='"')
        for table_name, column_names in tables.items():
            writer.writerow([table_name, *column_names])

    for table_name, column_names in tables.items():
        with (dest_path / f'{table_name}.csv').open('w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file, delimiter=';', quotechar='"')
            writer.writerow(column_names)

            column_names = [f"[{column_name}]" for column_name in column_names]
            q = f"SELECT {', '.join(column_names)} FROM {table_name}"
            c = cursor.execute(q)
            for row in c.fetchall():
                writer.writerow(row)


def test():
    with sqlite3.connect("../../user_data/database.sqlite") as connection:
        with closing(connection.cursor()) as cursor:
            table_names = ['Forwarding', ]

            path = Path('../../_/')

            q = ("INSERT INTO {table} "
                 "({columns}) "
                 "VALUES ({values})")

            def norm(c: str):
                if c == 'order':
                    return '[order]'
                return c

            for table_name in table_names:
                column_names = list(map(norm, get_column_names(cursor, table_name)))
                columns = ', '.join([f'{c}' for c in column_names])
                values = ', '.join(('?',) * len(column_names))

                if table_name == 'TelegramThreads':
                    columns = ', '.join([f'{c}' for c in column_names[1:3]])
                    values = ', '.join(('?',) * 2)

                csv_path = (path / table_name).with_suffix('.csv')
                with csv_path.open('r', encoding='utf-8', newline='') as file:
                    reader = csv.DictReader(file, delimiter=';', quotechar='"', dialect='excel')
                    for row in reader:
                        vs = tuple(row.values())
                        qf = q.format(table=table_name, columns=columns, values=values)
                        try:
                            cursor.execute(qf, vs)
                        except Exception as e:
                            print(qf, vs)
                            raise e
                    connection.commit()

            ths = {}
            q1 = "SELECT * FROM TelegramThreads"
            c1 = cursor.execute(q1)
            for row in c1.fetchall():
                ths[row[1]] = row[0]

            q2 = "SELECT * FROM Forwarding"
            q3 = "UPDATE Forwarding SET telegram_thread_id = ? WHERE id = ?"

            c2 = cursor.execute(q2)
            for row in c2.fetchall():
                f_id = row[0]
                th_n = row[3]
                if th_n:
                    print(row, ths[th_n])
                    cursor.execute(q3, (ths[th_n], f_id))

            connection.commit()


if __name__ == '__main__':
    test()
