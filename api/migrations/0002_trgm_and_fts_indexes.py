from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        # Activate pg_trgm extension
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;",
        ),
        # GIN trigram index on title for similarity search
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS news_checks_title_trgm_idx
                ON news_checks
                USING gin (title gin_trgm_ops);
            """,
            reverse_sql="DROP INDEX IF EXISTS news_checks_title_trgm_idx;",
        ),
        # GIN full-text index on title for full-text search
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS news_checks_title_fts_idx
                ON news_checks
                USING gin(to_tsvector('english', title));
            """,
            reverse_sql="DROP INDEX IF EXISTS news_checks_title_fts_idx;",
        ),
    ]