from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_news_source"),
    ]

    operations = [
        migrations.AlterField(
            model_name="newssource",
            name="name",
            field=models.CharField(max_length=200, unique=True, null=True, blank=True),
        ),
    ]