"""Add nlp_command field to rules table

Revision ID: 20241222000000
Revises: 20250919000000
Create Date: 2024-12-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20241222000000'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nlp_command field to rules table
    op.add_column('rules', sa.Column('nlp_command', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove nlp_command field from rules table
    op.drop_column('rules', 'nlp_command')
