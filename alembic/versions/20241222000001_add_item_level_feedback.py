"""Add item-level feedback table

Revision ID: 20241222000001
Revises: 20241222000000
Create Date: 2024-12-22 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241222000001'
down_revision = '20241222000000'
branch_labels = None
depends_on = None


def upgrade():
    # Create quote_item_feedback table
    op.create_table('quote_item_feedback',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('quote_item_id', sa.String(36), sa.ForeignKey('quote_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('quote_id', sa.String(36), sa.ForeignKey('quotes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('feedback_type', sa.String(50), nullable=False),  # 'correct', 'incorrect', 'missing', 'wrong_quantity', 'wrong_price', 'wrong_specs'
        sa.Column('rating', sa.Integer(), nullable=True),  # 1-5 rating for the specific item
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('suggested_sku', sa.String(255), nullable=True),  # If user suggests a different SKU
        sa.Column('suggested_quantity', sa.Integer(), nullable=True),  # If user suggests different quantity
        sa.Column('suggested_price', sa.Numeric(12, 2), nullable=True),  # If user suggests different price
        sa.Column('correction_data', postgresql.JSONB(), nullable=True),  # Structured correction data
        sa.Column('user_context', postgresql.JSONB(), nullable=True),  # Additional context about why this item was wrong
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    # Create indexes for better performance
    op.create_index('idx_quote_item_feedback_quote_item_id', 'quote_item_feedback', ['quote_item_id'])
    op.create_index('idx_quote_item_feedback_quote_id', 'quote_item_feedback', ['quote_id'])
    op.create_index('idx_quote_item_feedback_type', 'quote_item_feedback', ['feedback_type'])
    op.create_index('idx_quote_item_feedback_rating', 'quote_item_feedback', ['rating'])
    
    # Add item_metadata column to quote_items if it doesn't exist (for storing feedback insights)
    op.add_column('quote_items', sa.Column('feedback_insights', postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_table('quote_item_feedback')
    op.drop_column('quote_items', 'feedback_insights')
