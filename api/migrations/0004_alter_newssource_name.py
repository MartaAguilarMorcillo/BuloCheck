from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_news_sources"),
    ]

    operations = [
        migrations.AlterField(
            model_name="newssource",
            name="name",
            field=models.CharField(max_length=200, unique=True, null=True, blank=True),
        ),
    ]
