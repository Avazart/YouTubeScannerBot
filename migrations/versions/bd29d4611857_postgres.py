"""postgres

Revision ID: bd29d4611857
Revises: 447f9219817f
Create Date: 2023-04-10 15:11:09.248707

"""

import sqlalchemy
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bd29d4611857"
down_revision = "447f9219817f"
branch_labels = None
depends_on = None

big_int_targets = [
    (
        "TelegramChats",
        [
            "original_id",
        ],
    ),
    (
        "TelegramThreads",
        [
            "original_chat_id",
        ],
    ),
    (
        "Forwarding",
        [
            "telegram_chat_id",
        ],
    ),
]

nullable_targets = [
    ("TelegramChats", ["title", "first_name", "last_name", "is_creator"]),
    ("TelegramThreads", ["title"]),
    ("YouTubeVideos", ["title", "style", "time_ago", "creation_time"]),
]


def upgrade() -> None:
    connection: sqlalchemy.engine.base.Connection = op.get_bind()
    if connection.engine.name == "sqlite":
        for table, columns in big_int_targets:
            with op.batch_alter_table(table) as batch_op:
                for column in columns:
                    batch_op.alter_column(column, type_=sa.BIGINT)

        for table, columns in nullable_targets:
            with op.batch_alter_table(table) as batch_op:
                for column in columns:
                    batch_op.alter_column(column, nullable=True)
    else:  # Postgres
        for table, columns in big_int_targets:
            for column in columns:
                op.alter_column(table, column, type_=sa.BIGINT)

        for table, columns in nullable_targets:
            for column in columns:
                op.alter_column(table, column, nullable=True)


def downgrade() -> None:
    connection: sqlalchemy.engine.base.Connection = op.get_bind()
    if connection.engine.name == "sqlite":
        for table, columns in big_int_targets:
            with op.batch_alter_table(table) as batch_op:
                for column in columns:
                    batch_op.alter_column(column, type_=sa.INTEGER)

        for table, columns in nullable_targets:
            with op.batch_alter_table(table) as batch_op:
                for column in columns:
                    batch_op.alter_column(column, nullable=False)
    else:  # Postgres
        for table, columns in big_int_targets:
            for column in columns:
                op.alter_column(table, column, type_=sa.INTEGER)

        for table, columns in nullable_targets:
            for column in columns:
                op.alter_column(table, column, nullable=False)
