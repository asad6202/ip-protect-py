"""rename_metadata_to_item_metadata_in_quote_items

Revision ID: 024638403cab
Revises: 20241222000001
Create Date: 2025-09-24 10:46:43.478521

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '024638403cab'
down_revision = '20241222000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename metadata column to item_metadata in quote_items table
    op.alter_column('quote_items', 'metadata', new_column_name='item_metadata')


def downgrade() -> None:
    # Rename item_metadata column back to metadata in quote_items table
    op.alter_column('quote_items', 'item_metadata', new_column_name='metadata')