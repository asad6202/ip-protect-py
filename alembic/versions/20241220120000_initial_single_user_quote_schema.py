"""Initial single user quote schema

Revision ID: 20241220120000
Revises: 
Create Date: 2024-12-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241220120000'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable required PostgreSQL extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    
    # Try to create vector extension with graceful failure handling
    op.execute("""
        DO $$ 
        BEGIN 
            CREATE EXTENSION IF NOT EXISTS vector;
            RAISE NOTICE 'pgvector extension enabled successfully';
        EXCEPTION
            WHEN OTHERS THEN
                RAISE WARNING 'pgvector extension not available: %. The system will work with deterministic search only.', SQLERRM;
        END $$;
    """)

    # Create brands table
    op.create_table('brands',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('slug', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_unique_constraint('uq_brands_name', 'brands', ['name'])

    # Create product_uploads table
    op.create_table('product_uploads',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('brand_id', sa.String(36), nullable=True),
        sa.Column('original_name', sa.Text(), nullable=False),
        sa.Column('stored_path', sa.Text(), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default="'uploaded'"),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='SET NULL'),
        sa.CheckConstraint("status IN ('uploaded','processing','processed','failed')", name='ck_product_uploads_status')
    )

    # Create product_import_batches table
    op.create_table('product_import_batches',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('brand_id', sa.String(36), nullable=True),
        sa.Column('upload_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['upload_id'], ['product_uploads.id'], ondelete='SET NULL')
    )

    # Create products table
    op.create_table('products',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('brand_id', sa.String(36), nullable=True),
        sa.Column('sku', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('price', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.Text(), nullable=False),
        sa.Column('family', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('form_factor', sa.Text(), nullable=True),
        sa.Column('outdoor', sa.Boolean(), nullable=True),
        sa.Column('poe', sa.Boolean(), nullable=True),
        sa.Column('poe_plus', sa.Boolean(), nullable=True),
        sa.Column('ir_range_m', sa.Integer(), nullable=True),
        sa.Column('resolution_mp', sa.Numeric(), nullable=True),
        sa.Column('vandal_ik10', sa.Boolean(), nullable=True),
        sa.Column('nvr_channels', sa.Integer(), nullable=True),
        sa.Column('switch_ports', sa.Integer(), nullable=True),
        sa.Column('is_accessory', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('accessory_type', sa.Text(), nullable=True),
        sa.Column('search_text', sa.Text(), nullable=True),
        sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='SET NULL')
    )

    # Add computed tsvector column for products
    op.execute("""
        ALTER TABLE products 
        ADD COLUMN ts tsvector 
        GENERATED ALWAYS AS (to_tsvector('simple', coalesce(search_text, ''))) STORED
    """)

    # Create unique constraint on products
    op.create_unique_constraint('uq_products_brand_sku', 'products', ['brand_id', 'sku'])

    # Create indexes for products
    op.create_index('ix_products_brand_id', 'products', ['brand_id'])
    op.create_index('ix_products_family', 'products', ['family'])
    op.create_index('ix_products_price', 'products', ['price'])
    op.create_index('ix_products_active', 'products', ['active'])
    op.create_index('ix_products_is_accessory', 'products', ['is_accessory'])
    op.create_index('ix_products_nvr_channels', 'products', ['nvr_channels'])
    op.create_index('ix_products_switch_ports', 'products', ['switch_ports'])
    op.create_index('ix_products_ts', 'products', ['ts'], postgresql_using='gin')
    op.create_index('ix_products_description_trgm', 'products', ['description'], postgresql_using='gin', postgresql_ops={'description': 'gin_trgm_ops'})

    # Create product_embeddings table (with graceful vector extension handling)
    op.execute("""
        DO $$ 
        BEGIN 
            CREATE TABLE product_embeddings (
                product_id VARCHAR(36) PRIMARY KEY,
                embedding vector(1536)
            );
            ALTER TABLE product_embeddings 
            ADD CONSTRAINT fk_product_embeddings_product_id 
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE;
        EXCEPTION
            WHEN OTHERS THEN
                -- Create table without vector column if extension not available
                CREATE TABLE product_embeddings (
                    product_id VARCHAR(36) PRIMARY KEY,
                    embedding TEXT
                );
                ALTER TABLE product_embeddings 
                ADD CONSTRAINT fk_product_embeddings_product_id 
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE;
                RAISE WARNING 'Created product_embeddings table without vector column due to missing pgvector extension';
        END $$;
    """)

    # Create quotes table
    op.create_table('quotes',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('extracted_intent', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('currency', sa.Text(), nullable=True),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default="'draft'"),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.CheckConstraint("status IN ('draft','sent','accepted','rejected','expired')", name='ck_quotes_status')
    )

    # Create quote_items table
    op.create_table('quote_items',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('quote_id', sa.String(36), nullable=False),
        sa.Column('product_id', sa.String(36), nullable=True),
        sa.Column('sku', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.Text(), nullable=False),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.CheckConstraint('quantity >= 1', name='ck_quote_items_quantity')
    )
    op.create_index('ix_quote_items_quote_id', 'quote_items', ['quote_id'])

    # Create quote_feedback table
    op.create_table('quote_feedback',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('quote_id', sa.String(36), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('corrections', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
        sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_quote_feedback_rating')
    )
    op.create_index('ix_quote_feedback_quote_id', 'quote_feedback', ['quote_id'])

    # Create rule_sets table
    op.create_table('rule_sets',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_unique_constraint('uq_rule_sets_name', 'rule_sets', ['name'])

    # Create rules table
    op.create_table('rules',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('rule_set_id', sa.String(36), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('scope', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('condition', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['rule_set_id'], ['rule_sets.id'], ondelete='CASCADE'),
        sa.CheckConstraint("scope IN ('global','item')", name='ck_rules_scope')
    )
    op.create_index('ix_rules_rule_set_id', 'rules', ['rule_set_id'])

    # Create rule_executions table
    op.create_table('rule_executions',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('quote_id', sa.String(36), nullable=False),
        sa.Column('rule_id', sa.String(36), nullable=False),
        sa.Column('fired', sa.Boolean(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['rules.id'], ondelete='CASCADE')
    )
    op.create_index('ix_rule_executions_quote_id', 'rule_executions', ['quote_id'])

    # Create prompt_runs table
    op.create_table('prompt_runs',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('extracted_intent', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rules_applied', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result_quote_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['result_quote_id'], ['quotes.id'], ondelete='SET NULL')
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table('prompt_runs')
    op.drop_table('rule_executions')
    op.drop_table('rules')
    op.drop_table('rule_sets')
    op.drop_table('quote_feedback')
    op.drop_table('quote_items')
    op.drop_table('quotes')
    op.drop_table('product_embeddings')
    op.drop_table('products')
    op.drop_table('product_import_batches')
    op.drop_table('product_uploads')
    op.drop_table('brands')
    
    # Note: We don't drop extensions as they might be used by other applications
