"""
Створює зручності (фішки) та перераховує рівні мобільності для всіх об'єктів з аудитом.
Запуск: python manage.py add_features_and_levels
"""

from django.core.management.base import BaseCommand

from properties.models import AccessibilityAudit, Feature, Property

DEFAULT_FEATURES = [
    "Паркінг",
    "Балкон",
    "Пандус",
    "Безбар'єрний вхід",
    "Ліфт",
    "Консьєрж",
    "Відеодомофон",
    "Охорона",
    "Можна з тваринами",
    "Бойлер",
    "Пральна машина",
    "Є резервне живлення",
    "Кондиціонер",
    "Балкон/лоджія",
    "Посудомийна машина",
    "Вантажний ліфт",
    "Центральне опалення",
    "Wi-Fi",
    "Холодильник",
]


class Command(BaseCommand):
    help = "Створює зручності та оновлює рівні доступності для всіх об'єктів."

    def handle(self, *args, **options):
        for name in DEFAULT_FEATURES:
            Feature.objects.get_or_create(name=name)
        self.stdout.write(f"Зручності: {Feature.objects.count()} шт.")

        updated = 0
        for audit in AccessibilityAudit.objects.select_related("property").all():
            level = audit.compute_mobility_level()
            if audit.property.mobility_level != level:
                audit.property.mobility_level = level
                audit.property.save(update_fields=["mobility_level"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Оновлено рівні доступності: {updated} об'єктів."))
