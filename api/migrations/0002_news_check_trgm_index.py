from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        # First activate pg_trgm in whatever DB is being used (including test DB)
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;",
        ),
        # Then create the trigram index on title
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS news_checks_title_trgm_idx
                ON news_checks
                USING gin (title gin_trgm_ops);
            """,
            reverse_sql="DROP INDEX IF EXISTS news_checks_title_trgm_idx;",
        ),
    ]
