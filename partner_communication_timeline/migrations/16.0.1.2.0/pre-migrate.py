# -*- coding: utf-8 -*-

"""
Add pct_body_text column and GIN trigram index on mail_message.

The column is added here so the index exists before post-migrate
populates the data. Odoo ORM will detect the column already exists
and skip the ALTER TABLE.
"""


def migrate(cr, version):
    # Ensure pg_trgm extension is available (base_search_fuzzy installs it,
    # but we guard here to be safe).
    cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Add the columns if they do not exist yet.
    cr.execute("""
        ALTER TABLE mail_message
        ADD COLUMN IF NOT EXISTS pct_body_text text
    """)
    cr.execute("""
        ALTER TABLE mail_message
        ADD COLUMN IF NOT EXISTS pct_partner_id integer
    """)

    # Create the GIN trigram index for fast full-text-like searches.
    cr.execute("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'mail_message'
          AND indexname = 'mail_message_pct_body_text_gin_idx'
    """)
    if not cr.fetchone():
        cr.execute("""
            CREATE INDEX mail_message_pct_body_text_gin_idx
            ON mail_message USING gin (pct_body_text gin_trgm_ops)
        """)
