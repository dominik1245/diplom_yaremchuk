"""
Команда: python manage.py load_sample_properties
Додає прикладові оголошення та аудити для демонстрації роботи сайту.
"""

from django.core.management.base import BaseCommand

from properties.models import (
    AccessibilityAudit,
    BathroomType,
    Feature,
    ListingType,
    Property,
)

DEFAULT_FEATURES = [
    "Паркінг",
    "Балкон",
    "Пандус",
    "Безбар'єрний вхід",
    "Ліфт",
    "Консьєрж",
    "Відеодомофон",
]


SAMPLE_PROPERTIES = [
    {
        "name": "2-кімнатна квартира з пандусом",
        "listing_type": ListingType.SALE,
        "city": "Київ",
        "address": "вул. Хрещатик, 1",
        "price": 2_500_000,
        "rooms": 2,
        "area_sqm": 52.5,
        "description": "Квартира в центрі, широкі двері, без порогів. Підходить для людей на кріслах колісних.",
        "audit": {
            "entrance_access": 9,
            "entrance_comment": "Пандус, автоматичні двері",
            "lift_width_cm": 110,
            "lift_score": 10,
            "lift_comment": "Широкий ліфт",
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "bathroom_comment": "Душ-трап у підлогу",
            "thresholds_max_height_cm": 0,
            "thresholds_score": 10,
            "thresholds_comment": "Порогів немає",
            "turning_radius_exists": True,
            "turning_comment": "Достатньо місця для розвороту",
        },
    },
    {
        "name": "3-кімнатна на Подолі",
        "listing_type": ListingType.RENT,
        "city": "Київ",
        "address": "вул. Хорива, 12",
        "price": 18_000,
        "rooms": 3,
        "area_sqm": 78,
        "description": "Оренда на довгий термін. Ліфт відповідає нормам доступності.",
        "audit": {
            "entrance_access": 7,
            "entrance_comment": "Є пандус, двері стандартні",
            "lift_width_cm": 90,
            "lift_score": 8,
            "lift_comment": "Ліфт 90 см",
            "bathroom_type": BathroomType.SHOWER_TRAY,
            "bathroom_comment": "Душ з піддоном",
            "thresholds_max_height_cm": 1.5,
            "thresholds_score": 8,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "1-кімнатна, Львів",
        "listing_type": ListingType.SALE,
        "city": "Львів",
        "address": "вул. Франка, 45",
        "price": 1_100_000,
        "rooms": 1,
        "area_sqm": 32,
        "description": "Компактна квартира з адаптованим санвузлом.",
        "audit": {
            "entrance_access": 8,
            "lift_width_cm": 85,
            "lift_score": 9,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 0,
            "thresholds_score": 9,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "Студія біля метро",
        "listing_type": ListingType.RENT,
        "city": "Київ",
        "address": "пр. Перемоги, 88",
        "price": 12_000,
        "rooms": 1,
        "area_sqm": 28,
        "description": "Оренда студії. Новий будинок, широкий ліфт.",
        "audit": {
            "entrance_access": 9,
            "lift_width_cm": 100,
            "lift_score": 10,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 0,
            "thresholds_score": 10,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "4-кімнатна, родинна",
        "listing_type": ListingType.SALE,
        "city": "Одеса",
        "address": "вул. Дерибасівська, 22",
        "price": 4_200_000,
        "rooms": 4,
        "area_sqm": 120,
        "description": "Велика квартира з двома санвузлами. Один адаптований.",
        "audit": {
            "entrance_access": 6,
            "entrance_comment": "Потрібен допоміжний пандус",
            "lift_width_cm": 82,
            "lift_score": 7,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 2,
            "thresholds_score": 7,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "2-кімнатна, Дніпро",
        "listing_type": ListingType.RENT,
        "city": "Дніпро",
        "address": "пр. Яворницького, 100",
        "price": 14_000,
        "rooms": 2,
        "area_sqm": 48,
        "description": "Тихі район, зелений двор.",
        "audit": {
            "entrance_access": 5,
            "lift_width_cm": 75,
            "lift_score": 5,
            "bathroom_type": BathroomType.SHOWER_TRAY,
            "thresholds_max_height_cm": 3,
            "thresholds_score": 5,
            "turning_radius_exists": False,
        },
    },
    # Додаткові міста та квартири
    {
        "name": "1-кімнатна на Печерську",
        "listing_type": ListingType.SALE,
        "city": "Київ",
        "address": "вул. Липська, 15",
        "price": 1_800_000,
        "rooms": 1,
        "area_sqm": 38,
        "description": "Елітний район. Повністю адаптована для маломобільних.",
        "audit": {
            "entrance_access": 10,
            "entrance_comment": "Пандус, автоматичні двері",
            "lift_width_cm": 120,
            "lift_score": 10,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 0,
            "thresholds_score": 10,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "2-кімнатна оренда, Оболонь",
        "listing_type": ListingType.RENT,
        "city": "Київ",
        "address": "пр. Оболонський, 25",
        "price": 16_000,
        "rooms": 2,
        "area_sqm": 55,
        "description": "Біля Дніпра, тихо. Ліфт 95 см, без порогів.",
        "audit": {
            "entrance_access": 8,
            "lift_width_cm": 95,
            "lift_score": 9,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 0,
            "thresholds_score": 9,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "3-кімнатна у центрі Львова",
        "listing_type": ListingType.SALE,
        "city": "Львів",
        "address": "пл. Ринок, 8",
        "price": 2_800_000,
        "rooms": 3,
        "area_sqm": 72,
        "description": "Історичний центр. Вхід з пандусом, ліфт відповідає нормам.",
        "audit": {
            "entrance_access": 7,
            "lift_width_cm": 88,
            "lift_score": 8,
            "bathroom_type": BathroomType.SHOWER_TRAY,
            "thresholds_max_height_cm": 1,
            "thresholds_score": 8,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "Студія оренда, Львів",
        "listing_type": ListingType.RENT,
        "city": "Львів",
        "address": "вул. Городоцька, 120",
        "price": 8_500,
        "rooms": 1,
        "area_sqm": 26,
        "description": "Новий будинок, душ-трап, широкий ліфт.",
        "audit": {
            "entrance_access": 9,
            "lift_width_cm": 105,
            "lift_score": 10,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 0,
            "thresholds_score": 10,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "2-кімнатна біля моря",
        "listing_type": ListingType.SALE,
        "city": "Одеса",
        "address": "вул. Аркадіївська, 5",
        "price": 3_500_000,
        "rooms": 2,
        "area_sqm": 58,
        "description": "За 5 хв до пляжу. Адаптований санвузол.",
        "audit": {
            "entrance_access": 8,
            "lift_width_cm": 92,
            "lift_score": 9,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 0,
            "thresholds_score": 9,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "1-кімнатна оренда, Одеса",
        "listing_type": ListingType.RENT,
        "city": "Одеса",
        "address": "вул. Преображенська, 30",
        "price": 10_000,
        "rooms": 1,
        "area_sqm": 35,
        "description": "Центр, поруч ринок та транспорт.",
        "audit": {
            "entrance_access": 6,
            "lift_width_cm": 80,
            "lift_score": 7,
            "bathroom_type": BathroomType.SHOWER_TRAY,
            "thresholds_max_height_cm": 2,
            "thresholds_score": 7,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "3-кімнатна, Харків",
        "listing_type": ListingType.SALE,
        "city": "Харків",
        "address": "вул. Сумська, 50",
        "price": 2_200_000,
        "rooms": 3,
        "area_sqm": 68,
        "description": "Головна вулиця міста. Ліфт 90 см, без порогів.",
        "audit": {
            "entrance_access": 8,
            "lift_width_cm": 90,
            "lift_score": 9,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 0,
            "thresholds_score": 9,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "2-кімнатна оренда, Харків",
        "listing_type": ListingType.RENT,
        "city": "Харків",
        "address": "пр. Науки, 45",
        "price": 12_000,
        "rooms": 2,
        "area_sqm": 48,
        "description": "Біля метро. Підходить для людей з обмеженою мобільністю.",
        "audit": {
            "entrance_access": 7,
            "lift_width_cm": 85,
            "lift_score": 8,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 1,
            "thresholds_score": 8,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "Студія, Запоріжжя",
        "listing_type": ListingType.RENT,
        "city": "Запоріжжя",
        "address": "пр. Соборний, 88",
        "price": 7_000,
        "rooms": 1,
        "area_sqm": 30,
        "description": "Новий будинок, повна доступність.",
        "audit": {
            "entrance_access": 9,
            "lift_width_cm": 100,
            "lift_score": 10,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 0,
            "thresholds_score": 10,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "2-кімнатна, Вінниця",
        "listing_type": ListingType.SALE,
        "city": "Вінниця",
        "address": "вул. Соборна, 60",
        "price": 1_400_000,
        "rooms": 2,
        "area_sqm": 52,
        "description": "Центр міста. Є пандус та широкий ліфт.",
        "audit": {
            "entrance_access": 8,
            "lift_width_cm": 88,
            "lift_score": 8,
            "bathroom_type": BathroomType.SHOWER_TRAY,
            "thresholds_max_height_cm": 1,
            "thresholds_score": 8,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "1-кімнатна оренда, Чернівці",
        "listing_type": ListingType.RENT,
        "city": "Чернівці",
        "address": "вул. Главна, 42",
        "price": 6_500,
        "rooms": 1,
        "area_sqm": 28,
        "description": "Тиха локація. Душ-трап, без порогів.",
        "audit": {
            "entrance_access": 7,
            "lift_width_cm": 82,
            "lift_score": 8,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 0,
            "thresholds_score": 9,
            "turning_radius_exists": True,
        },
    },
    {
        "name": "3-кімнатна, Івано-Франківськ",
        "listing_type": ListingType.SALE,
        "city": "Івано-Франківськ",
        "address": "вул. Незалежності, 15",
        "price": 1_900_000,
        "rooms": 3,
        "area_sqm": 75,
        "description": "Велика квартира з адаптованим санвузлом та кухнею.",
        "audit": {
            "entrance_access": 8,
            "lift_width_cm": 90,
            "lift_score": 9,
            "bathroom_type": BathroomType.SHOWER_DRAIN,
            "thresholds_max_height_cm": 0,
            "thresholds_score": 9,
            "turning_radius_exists": True,
        },
    },
]


class Command(BaseCommand):
    help = "Додає прикладові оголошення та аудити для демо-сайту."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Спочатку видалити всі оголошення та аудити.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            AccessibilityAudit.objects.all().delete()
            Property.objects.all().delete()
            self.stdout.write("Існуючі оголошення видалено.")

        for name in DEFAULT_FEATURES:
            Feature.objects.get_or_create(name=name)

        created = 0
        for i, data in enumerate(SAMPLE_PROPERTIES):
            audit_data = data.pop("audit")
            prop, was_created = Property.objects.get_or_create(
                name=data["name"],
                address=data["address"],
                defaults={
                    **data,
                    "is_published": True,
                },
            )
            if was_created:
                created += 1
                audit = AccessibilityAudit(property=prop, **audit_data)
                audit.save()
                # Додаємо зручності для демо
                lift_f = Feature.objects.filter(name="Ліфт").first()
                ramp_f = Feature.objects.filter(name="Пандус").first()
                if lift_f:
                    prop.features.add(lift_f)
                if ramp_f:
                    prop.features.add(ramp_f)
                if i % 3 == 0:
                    balcony = Feature.objects.filter(name="Балкон").first()
                    if balcony:
                        prop.features.add(balcony)
                if i % 4 == 0:
                    parking = Feature.objects.filter(name="Паркінг").first()
                    if parking:
                        prop.features.add(parking)
                self.stdout.write(f"  Додано: {prop.name}")

        self.stdout.write(self.style.SUCCESS(f"Готово. Створено оголошень: {created}"))
