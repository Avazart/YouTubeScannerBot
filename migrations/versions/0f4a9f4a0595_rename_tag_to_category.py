"""rename_Tag_to_Category

Revision ID: 0f4a9f4a0595
Revises: 2037534d665c
Create Date: 2023-10-17 14:51:09.010052

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '0f4a9f4a0595'
down_revision = '2037534d665c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table('Tags', 'Categories')
    op.rename_table('YouTubeChannelTags', 'YTChannelCategories')
    op.alter_column('YTChannelCategories', 'tag_id',
                    new_column_name='category_id')


def downgrade() -> None:
    op.rename_table('Categories', 'Tags')
    op.rename_table('YTChannelCategories', 'YouTubeChannelTags')
    op.alter_column('YTChannelCategories', 'category_id',
                    new_column_name='tag_id')
