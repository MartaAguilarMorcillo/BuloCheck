from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_news_check_trgm_index"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS news_checks_title_fts_idx
                ON news_checks
                USING gin(to_tsvector('english', title));
            """,
            reverse_sql="DROP INDEX IF EXISTS news_checks_title_fts_idx;",
        )
    ]