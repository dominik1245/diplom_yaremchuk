# Generated migration: усі зручності з фільтрів (як на референсі) — для каталогу та форми «Додати оголошення»

from django.db import migrations


FEATURES_FROM_PHOTO = [
    'Балкон',
    'Безбар\'єрний вхід',
    'Відеодомофон',
    'Консьєрж',
    'Ліфт',
    'Охорона',
    'Пандус',
    'Паркінг',
    'Можна з тваринами',
    'Бойлер',
    'Пральна машина',
    'Є резервне живлення',
    'Кондиціонер',
    'Балкон/лоджія',
    'Посудомийна машина',
    'Вантажний ліфт',
    'Центральне опалення',
    'Wi-Fi',
    'Холодильник',
]


def ensure_features(apps, schema_editor):
    Feature = apps.get_model('properties', 'Feature')
    for name in FEATURES_FROM_PHOTO:
        Feature.objects.get_or_create(name=name)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0008_add_more_amenity_features'),
    ]

    operations = [
        migrations.RunPython(ensure_features, noop),
    ]
