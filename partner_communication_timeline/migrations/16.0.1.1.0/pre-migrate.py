# -*- coding: utf-8 -*-

"""
Add performance indexes on mail_message for the communication timeline.

Indexes added:
- mail_message_date_idx: speeds up ORDER BY date DESC (global timeline)
- mail_message_message_type_idx: speeds up WHERE message_type IN (...)
- mail_message_date_message_type_idx: composite for the most common query pattern
- mail_message_email_from_gin_idx: GIN trigram index for ILIKE '%...%' searches on email_from
  (B-tree on lower(email_from) would only help prefix matches, not substring patterns)
"""

INDEXES = [
    (
        "mail_message_date_idx",
        "CREATE INDEX mail_message_date_idx ON mail_message (date DESC)",
    ),
    (
        "mail_message_message_type_idx",
        "CREATE INDEX mail_message_message_type_idx ON mail_message (message_type)",
    ),
    (
        "mail_message_date_message_type_idx",
        "CREATE INDEX mail_message_date_message_type_idx ON mail_message (message_type, date DESC)",
    ),
    (
        "mail_message_email_from_gin_idx",
        "CREATE INDEX mail_message_email_from_gin_idx ON mail_message USING gin (email_from gin_trgm_ops)",
    ),
]


def migrate(cr, version):
    # Ensure pg_trgm extension is available (required for gin_trgm_ops indexes).
    cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    cr.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'mail_message'
          AND indexname IN %s
    """, [tuple(name for name, _ in INDEXES)])
    existing = {row[0] for row in cr.fetchall()}

    for name, ddl in INDEXES:
        if name not in existing:
            cr.execute(ddl)
