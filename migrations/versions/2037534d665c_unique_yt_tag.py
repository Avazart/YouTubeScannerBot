"""unique_yt_tag

Revision ID: 2037534d665c
Revises: bd29d4611857
Create Date: 2023-04-15 13:23:35.906918

"""
import sqlalchemy
from alembic import op

# revision identifiers, used by Alembic.
revision = '2037534d665c'
down_revision = 'bd29d4611857'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection: sqlalchemy.engine.base.Connection = op.get_bind()
    if connection.engine.name == 'sqlite':
        with op.batch_alter_table('YouTubeChannelTags') as batch_op:
            batch_op.create_unique_constraint('unique_yt_tag',
                                              ['tag_id', 'channel_id'])
    else:
        op.create_unique_constraint('unique_yt_tag',
                                    'YouTubeChannelTags',
                                    ['tag_id', 'channel_id'])


def downgrade() -> None:
    connection: sqlalchemy.engine.base.Connection = op.get_bind()
    if connection.engine.name == 'sqlite':
        with op.batch_alter_table('YouTubeChannelTags') as batch_op:
            batch_op.drop_constraint('unique_yt_tag',
                                     type_='unique')
    else:
        op.drop_constraint('unique_yt_tag',
                           'YouTubeChannelTags',
                           type_='unique')
