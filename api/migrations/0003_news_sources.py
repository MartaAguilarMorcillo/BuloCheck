"""
Migration 0004 — Create NewsSource table and load the 47 predefined sources.

NewsSource stores the name, domain and logo URL of known news outlets.
The 47 predefined sources are loaded as initial data in this migration.
New sources discovered at prediction time are created on the fly with
is_predefined=False and no logo (resolved later via Clearbit API).
"""

from django.db import migrations

PREDEFINED_SOURCES = [
    (
        "BBC",
        "bbc.com",
        "https://upload.wikimedia.org/wikipedia/commons/4/41/BBC_Logo_2021.svg",
    ),
    (
        "The New York Times",
        "nytimes.com",
        "https://upload.wikimedia.org/wikipedia/commons/7/77/The_New_York_Times_logo.png",
    ),
    (
        "The Guardian",
        "theguardian.com",
        "https://upload.wikimedia.org/wikipedia/commons/7/75/The_Guardian_2018.svg",
    ),
    (
        "Reuters",
        "reuters.com",
        "https://upload.wikimedia.org/wikipedia/commons/b/b5/Reuters_logo.svg",
    ),
    (
        "Associated Press",
        "apnews.com",
        "https://upload.wikimedia.org/wikipedia/commons/0/0c/Associated_Press_logo_2012.svg",
    ),
    ("CNN", "cnn.com", "https://upload.wikimedia.org/wikipedia/commons/b/b1/CNN.svg"),
    (
        "Fox News",
        "foxnews.com",
        "https://upload.wikimedia.org/wikipedia/commons/6/67/Fox_News_Channel_logo.svg",
    ),
    (
        "The Washington Post",
        "washingtonpost.com",
        "https://upload.wikimedia.org/wikipedia/commons/9/93/The_Logo_of_The_Washington_Post_Newspaper.svg",
    ),
    (
        "Al Jazeera",
        "aljazeera.com",
        "https://upload.wikimedia.org/wikipedia/commons/e/e0/Al_Jazeera_Logo.svg",
    ),
    (
        "NPR",
        "npr.org",
        "https://upload.wikimedia.org/wikipedia/commons/d/d7/National_Public_Radio_logo.svg",
    ),
    (
        "The Times",
        "thetimes.com",
        "https://upload.wikimedia.org/wikipedia/commons/0/02/The_Times_masthead.svg",
    ),
    (
        "The Independent",
        "independent.co.uk",
        "https://upload.wikimedia.org/wikipedia/commons/6/6f/The_Independent_logo_2022.svg",
    ),
    (
        "BuzzFeed News",
        "buzzfeednews.com",
        "https://upload.wikimedia.org/wikipedia/commons/e/e4/BuzzFeed.svg",
    ),
    (
        "Vice",
        "vice.com",
        "https://upload.wikimedia.org/wikipedia/commons/6/64/Vice_logo.svg",
    ),
    (
        "Politico",
        "politico.com",
        "https://upload.wikimedia.org/wikipedia/commons/1/11/POLITICOLOGO.svg",
    ),
    (
        "The Hill",
        "thehill.com",
        "https://upload.wikimedia.org/wikipedia/commons/c/c3/Logo_The_Hill.svg",
    ),
    (
        "Vox",
        "vox.com",
        "https://upload.wikimedia.org/wikipedia/commons/a/a2/Vox_logo.svg",
    ),
    (
        "Axios",
        "axios.com",
        "https://upload.wikimedia.org/wikipedia/commons/c/c8/Axios_logo_%282020%29.svg",
    ),
    (
        "Bloomberg",
        "bloomberg.com",
        "https://upload.wikimedia.org/wikipedia/commons/5/5d/Bloomberg_logo.svg",
    ),
    (
        "Forbes",
        "forbes.com",
        "https://upload.wikimedia.org/wikipedia/commons/8/8b/Forbes_logo.svg",
    ),
    (
        "Time",
        "time.com",
        "https://upload.wikimedia.org/wikipedia/commons/b/b3/Time_Magazine_logo.svg",
    ),
    (
        "Newsweek",
        "newsweek.com",
        "https://upload.wikimedia.org/wikipedia/commons/d/db/Newsweek_Logo.svg",
    ),
    (
        "The Atlantic",
        "theatlantic.com",
        "https://upload.wikimedia.org/wikipedia/commons/b/b4/The_Atlantic_magazine_logo.svg",
    ),
    (
        "Slate",
        "slate.com",
        "https://upload.wikimedia.org/wikipedia/commons/4/4a/Slate_new_logo.svg",
    ),
    (
        "Salon",
        "salon.com",
        "https://upload.wikimedia.org/wikipedia/commons/2/26/Salon_logo_2021.svg",
    ),
    (
        "Breitbart",
        "breitbart.com",
        "https://upload.wikimedia.org/wikipedia/commons/f/fe/Breitbart_News.svg",
    ),
    (
        "Daily Mail",
        "dailymail.com",
        "https://upload.wikimedia.org/wikipedia/commons/6/6e/Daily_Mail_Logo.svg",
    ),
    (
        "The Sun",
        "thesun.co.uk",
        "https://upload.wikimedia.org/wikipedia/commons/3/3b/The_Sun.svg",
    ),
    (
        "Sky News",
        "news.sky.com",
        "https://upload.wikimedia.org/wikipedia/commons/8/84/Sky_News_Logo.svg",
    ),
    (
        "MSNBC",
        "msnbc.com",
        "https://upload.wikimedia.org/wikipedia/commons/5/50/MSNBC_2015-2021_logo.svg",
    ),
    (
        "ABC News",
        "abcnews.com",
        "https://upload.wikimedia.org/wikipedia/commons/2/2a/ABC_News_logo_2021.svg",
    ),
    (
        "CBS News",
        "cbsnews.com",
        "https://upload.wikimedia.org/wikipedia/commons/d/dc/CBS_News_logo_%282020%29.svg",
    ),
    (
        "NBC News",
        "nbcnews.com",
        "https://upload.wikimedia.org/wikipedia/commons/9/97/NBC_News_logo.png",
    ),
    (
        "USA Today",
        "usatoday.com",
        "https://upload.wikimedia.org/wikipedia/commons/f/fe/USA_Today_%282020-01-29%29.svg",
    ),
    (
        "Los Angeles Times",
        "latimes.com",
        "https://upload.wikimedia.org/wikipedia/commons/1/18/Los_Angeles_Times_logo.svg",
    ),
    (
        "Chicago Tribune",
        "chicagotribune.com",
        "https://upload.wikimedia.org/wikipedia/commons/c/c4/Chicago_Tribune_Logo.svg",
    ),
    (
        "The Wall Street Journal",
        "wsj.com",
        "https://upload.wikimedia.org/wikipedia/commons/4/4a/WSJ_Logo.svg",
    ),
    (
        "Financial Times",
        "ft.com",
        "https://upload.wikimedia.org/wikipedia/commons/b/b0/Financial-times-logo.svg",
    ),
    (
        "The Economist",
        "economist.com",
        "https://upload.wikimedia.org/wikipedia/commons/6/65/The_Economist_Logo.svg",
    ),
    (
        "Wired",
        "wired.com",
        "https://upload.wikimedia.org/wikipedia/commons/9/95/Wired_logo.svg",
    ),
    (
        "TechCrunch",
        "techcrunch.com",
        "https://upload.wikimedia.org/wikipedia/commons/7/7f/TechCrunch_Logo_2013.png",
    ),
    (
        "Ars Technica",
        "arstechnica.com",
        "https://upload.wikimedia.org/wikipedia/commons/5/51/Ars_Technica_logo_%282016%29.svg",
    ),
    (
        "The Verge",
        "theverge.com",
        "https://upload.wikimedia.org/wikipedia/commons/a/af/The_Verge_logo.svg",
    ),
    (
        "Mashable",
        "mashable.com",
        "https://upload.wikimedia.org/wikipedia/commons/3/3a/Mashable_Logo_%282021%29.svg",
    ),
    (
        "HuffPost",
        "huffpost.com",
        "https://upload.wikimedia.org/wikipedia/commons/5/5a/HuffPost.svg",
    ),
    (
        "Daily Beast",
        "thedailybeast.com",
        "https://upload.wikimedia.org/wikipedia/commons/a/af/The_Daily_Beast_%28logo%29.svg",
    ),
    ("Times of Israel", "timesofisrael.com", None),
]


def load_predefined_sources(apps, schema_editor):
    NewsSource = apps.get_model("api", "NewsSource")
    for name, domain, logo_url in PREDEFINED_SOURCES:
        NewsSource.objects.create(
            name=name,
            domain=domain,
            logo_url=logo_url,
            is_predefined=True,
        )


def unload_predefined_sources(apps, schema_editor):
    NewsSource = apps.get_model("api", "NewsSource")
    NewsSource.objects.filter(is_predefined=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_trgm_and_fts_indexes"),
    ]

    operations = [
        migrations.RunPython(load_predefined_sources, unload_predefined_sources),
    ]