"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-01-08 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================================
    # 1. RSS Feeds
    # ============================================================================
    op.create_table(
        'feeds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('last_modified', sa.Text(), nullable=True),
        sa.Column('etag', sa.Text(), nullable=True),
        sa.Column('pull_interval', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url')
    )
    op.create_index('idx_feeds_active', 'feeds', ['active'])
    op.create_index('idx_feeds_updated_at', 'feeds', ['updated_at'])

    # ============================================================================
    # 2. Feed Items (News/Posts)
    # ============================================================================
    op.create_table(
        'items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('feed_id', sa.Integer(), nullable=False),
        sa.Column('guid', sa.Text(), nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.Text(), nullable=True),
        sa.Column('published_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=True),
        sa.Column('processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['feed_id'], ['feeds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('feed_id', 'guid', name='uq_items_feed_guid')
    )
    op.create_index('idx_items_feed_id', 'items', ['feed_id'])
    op.create_index('idx_items_processed', 'items', ['processed'])
    op.create_index('idx_items_published_at', 'items', ['published_at'], postgresql_using='btree', postgresql_ops={'published_at': 'DESC'})
    op.create_index('idx_items_content_hash', 'items', ['content_hash'])

    # ============================================================================
    # 3. AI Rewrites
    # ============================================================================
    op.create_table(
        'rewrites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('rewritten_title', sa.Text(), nullable=True),
        sa.Column('rewritten_text', sa.Text(), nullable=True),
        sa.Column('bullets_json', sa.Text(), nullable=True),
        sa.Column('tokens_in', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('tokens_out', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('cost_usd', sa.Numeric(), nullable=True, server_default='0.0'),
        sa.Column('status', sa.Text(), nullable=False, server_default='queued'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_id')
    )
    op.create_index('idx_rewrites_status', 'rewrites', ['status'])
    op.create_index('idx_rewrites_item_id', 'rewrites', ['item_id'])

    # ============================================================================
    # 4. Telegram Chats/Channels
    # ============================================================================
    op.create_table(
        'chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('username', sa.Text(), nullable=True),
        sa.Column('chat_type', sa.Text(), nullable=True, server_default='group'),
        sa.Column('ai_enabled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('language', sa.Text(), nullable=True, server_default='ru'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id')
    )
    op.create_index('idx_chats_chat_id', 'chats', ['chat_id'])
    op.create_index('idx_chats_ai_enabled', 'chats', ['ai_enabled'])

    # ============================================================================
    # 5. Subscriptions (Many-to-Many: Chats <-> Feeds)
    # ============================================================================
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('feed_id', sa.Integer(), nullable=False),
        sa.Column('filters_json', sa.Text(), nullable=True),
        sa.Column('active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['feed_id'], ['feeds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id', 'feed_id', name='uq_subscriptions_chat_feed')
    )
    op.create_index('idx_subscriptions_chat_id', 'subscriptions', ['chat_id'])
    op.create_index('idx_subscriptions_feed_id', 'subscriptions', ['feed_id'])
    op.create_index('idx_subscriptions_active', 'subscriptions', ['active'])

    # ============================================================================
    # 6. Deliveries (Message Sending Log)
    # ============================================================================
    op.create_table(
        'deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id', 'item_id', name='uq_deliveries_chat_item')
    )
    op.create_index('idx_deliveries_chat_id', 'deliveries', ['chat_id'])
    op.create_index('idx_deliveries_item_id', 'deliveries', ['item_id'])
    op.create_index('idx_deliveries_status', 'deliveries', ['status'])
    op.create_index('idx_deliveries_sent_at', 'deliveries', ['sent_at'], postgresql_using='btree', postgresql_ops={'sent_at': 'DESC'})

    # ============================================================================
    # 7. Error Log
    # ============================================================================
    op.create_table(
        'errors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('context', sa.Text(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('traceback', sa.Text(), nullable=True),
        sa.Column('related_table', sa.Text(), nullable=True),
        sa.Column('related_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_errors_context', 'errors', ['context'])
    op.create_index('idx_errors_created_at', 'errors', ['created_at'], postgresql_using='btree', postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_errors_related', 'errors', ['related_table', 'related_id'])

    # ============================================================================
    # 8. Users (Telegram Users)
    # ============================================================================
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_users_username', 'users', ['username'])

    # ============================================================================
    # 9. Daily Metrics (Aggregated)
    # ============================================================================
    op.create_table(
        'metrics_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('items_processed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('rewrites_done', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('ai_cost_usd', sa.Numeric(), nullable=True, server_default='0.0'),
        sa.Column('messages_sent', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('messages_failed', sa.Integer(), nullable=True, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index('idx_metrics_date', 'metrics_daily', ['date'], postgresql_using='btree', postgresql_ops={'date': 'DESC'})

    # ============================================================================
    # Triggers for auto-updating updated_at
    # ============================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    op.execute("""
        CREATE TRIGGER update_feeds_timestamp
        BEFORE UPDATE ON feeds
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_rewrites_timestamp
        BEFORE UPDATE ON rewrites
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_chats_timestamp
        BEFORE UPDATE ON chats
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_chats_timestamp ON chats;")
    op.execute("DROP TRIGGER IF EXISTS update_rewrites_timestamp ON rewrites;")
    op.execute("DROP TRIGGER IF EXISTS update_feeds_timestamp ON feeds;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop tables in reverse order
    op.drop_table('metrics_daily')
    op.drop_table('users')
    op.drop_table('errors')
    op.drop_table('deliveries')
    op.drop_table('subscriptions')
    op.drop_table('chats')
    op.drop_table('rewrites')
    op.drop_table('items')
    op.drop_table('feeds')
