"""
Моделі платформи «Доступний Дім».
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

SCORE_VALIDATORS = [MinValueValidator(1), MaxValueValidator(10)]


def score_to_status(score):
    """
    Перетворює бал (1–10) на текстовий статус доступності.
    9–10: Ідеально
    6–8: Потребує покращення
    3–5: Важкодоступно
    1–2: Недоступно
    """
    if score is None:
        return None
    if score >= 9:
        return "ideal"
    if score >= 6:
        return "needs_improvement"
    if score >= 3:
        return "difficult"
    return "inaccessible"


class ListingType(models.TextChoices):
    """Тип оголошення."""

    SALE = "sale", "Продаж"
    RENT = "rent", "Оренда"


class Feature(models.Model):
    """Фішка / зручність об'єкта (балкон, паркінг, пандус тощо)."""
    CATEGORY_CHOICES = [
        ('apartment', 'В квартирі'),
        ('building', 'В будинку та на території'),
        ('rules', 'Правила проживання'),
    ]

    name = models.CharField("Назва", max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    category = models.CharField("Категорія", max_length=20, choices=CATEGORY_CHOICES, default='apartment')

    class Meta:
        verbose_name = "Зручність"
        verbose_name_plural = "Зручності"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            import uuid
            self.slug = slugify(self.name, allow_unicode=True)
            if not self.slug:
                self.slug = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Property(models.Model):
    """Об'єкт нерухомості."""

    name = models.CharField("Назва", max_length=255)
    listing_type = models.CharField(
        "Тип", max_length=10, choices=ListingType.choices, default=ListingType.SALE
    )
    address = models.CharField("Адреса", max_length=500)
    city = models.CharField("Місто", max_length=100, blank=True)
    price = models.DecimalField(
        "Ціна (грн)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    rooms = models.PositiveSmallIntegerField("Кількість кімнат", null=True, blank=True)
    area_sqm = models.FloatField(
        "Площа (м²)", null=True, blank=True, validators=[MinValueValidator(1)]
    )
    description = models.TextField("Опис", blank=True)
    photo = models.ImageField("Фото", upload_to="properties/", null=True, blank=True)
    features = models.ManyToManyField(Feature, blank=True, verbose_name="Зручності")
    mobility_level = models.PositiveSmallIntegerField(
        "Рівень доступності (1–5)",
        null=True,
        blank=True,
        help_text="1 = батьки з дитиною, 2 = без руки, 3 = крісло, 4 = без руки/ноги, 5 = універсальний",
    )
    is_published = models.BooleanField("Опубліковано", default=True)
    is_featured = models.BooleanField(
        "Підвищена видимість (платне)",
        default=False,
        help_text="Оголошення показується вище в каталозі.",
    )
    featured_until = models.DateTimeField(
        "Реклама до",
        null=True,
        blank=True,
        help_text="До якої дати діє підвищена видимість.",
    )
    view_count = models.PositiveIntegerField("Перегляди", default=0)
    contact_phone = models.CharField("Контактний телефон", max_length=30, blank=True)
    is_verified = models.BooleanField(
        "Перевірене оголошення",
        default=False,
        help_text="Позначка, що нерухомість реальна (перевірено адміністрацією).",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="properties",
        verbose_name="Власник оголошення",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Об'єкт нерухомості"
        verbose_name_plural = "Об'єкти нерухомості"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class PropertyPhoto(models.Model):
    """Додаткове фото оголошення (галерея)."""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="extra_photos",
        verbose_name="Оголошення",
    )
    image = models.ImageField("Фото", upload_to="properties/gallery/%Y/%m/")
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Фото оголошення"
        verbose_name_plural = "Фото оголошень"
        ordering = ["order", "id"]

    def __str__(self):
        return f"Фото #{self.order} — {self.property.name}"


class PropertyFavorite(models.Model):
    """Обране оголошення користувача."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_favorites",
        verbose_name="Користувач",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Оголошення",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Обране оголошення"
        verbose_name_plural = "Обрані оголошення"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "property"], name="unique_user_property_favorite"
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} — {self.property.name}"


class EntranceStatus(models.TextChoices):
    """Статус доступності входу."""

    INACCESSIBLE = "inaccessible", "Недоступно"
    DIFFICULT = "difficult", "Важкодоступно"
    NEEDS_IMPROVEMENT = "needs_improvement", "Потребує покращення"
    IDEAL = "ideal", "Ідеально"


class BathroomType(models.TextChoices):
    """Тип санвузлу."""

    BATH = "bath", "Ванна"
    SHOWER_TRAY = "shower_tray", "Душ з піддоном"
    SHOWER_DRAIN = "shower_drain", "Душ-трап у підлогу"


class AccessibilityAudit(models.Model):
    """Аудит доступності об'єкта (OneToOne з Property)."""

    property = models.OneToOneField(
        Property, on_delete=models.CASCADE, related_name="audit", verbose_name="Об'єкт"
    )
    # Вхід
    entrance_access = models.PositiveSmallIntegerField(
        "Доступність входу (1–10)", null=True, blank=True, validators=SCORE_VALIDATORS
    )
    entrance_status = models.CharField(
        "Статус входу", max_length=20, choices=EntranceStatus.choices, blank=True
    )
    entrance_comment = models.CharField("Коментар (вхід)", max_length=500, blank=True)
    # Ліфт
    lift_width_cm = models.PositiveIntegerField("Ширина ліфта (см)", null=True, blank=True)
    lift_score = models.PositiveSmallIntegerField(
        "Бал ліфта (1–10)", null=True, blank=True, validators=SCORE_VALIDATORS
    )
    lift_comment = models.CharField("Коментар (ліфт)", max_length=500, blank=True)
    # Санвузол
    bathroom_type = models.CharField(
        "Тип санвузлу", max_length=20, choices=BathroomType.choices, blank=True
    )
    bathroom_comment = models.CharField("Коментар (санвузол)", max_length=500, blank=True)
    # Пороги
    thresholds_max_height_cm = models.FloatField("Макс. висота порогів (см)", null=True, blank=True)
    thresholds_score = models.PositiveSmallIntegerField(
        "Бал порогів (1–10)", null=True, blank=True, validators=SCORE_VALIDATORS
    )
    thresholds_comment = models.CharField("Коментар (пороги)", max_length=500, blank=True)
    # Поворотний діаметр
    turning_radius_exists = models.BooleanField("Наявність радіусу для розвороту", default=False)
    turning_comment = models.CharField("Коментар (розворот)", max_length=500, blank=True)
    # Загальний бал (середнє)
    total_score = models.FloatField("Загальний бал", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Аудит доступності"
        verbose_name_plural = "Аудити доступності"

    def __str__(self):
        return f"Аудит: {self.property.name}"

    def _scores_for_average(self):
        """Збирає бали для розрахунку середнього (тільки числові 1–10)."""
        parts = []
        if self.entrance_access is not None:
            parts.append(self.entrance_access)
        if self.lift_score is not None:
            parts.append(self.lift_score)
        if self.thresholds_score is not None:
            parts.append(self.thresholds_score)
        if self.turning_radius_exists is not None:
            parts.append(10 if self.turning_radius_exists else 0)
        return parts

    def recalculate_total_score(self):
        """Розраховує та зберігає total_score як середнє балів."""
        parts = self._scores_for_average()
        if not parts:
            self.total_score = None
            return
        self.total_score = round(sum(parts) / len(parts), 1)

    def get_status_from_score(self, score):
        """Повертає ключ статусу за балом (для відображення)."""
        return score_to_status(score)

    def compute_mobility_level(self):
        """
        Визначає рівень доступності (1–5).
        1 = базова, 2–4 = проміжні, 5 = універсальна доступність (найвищі вимоги).
        """
        if self.entrance_access is None or self.entrance_access < 3:
            return None
        # Рівень 1: мінімум — вхід >= 3
        level = 1
        if self.entrance_access >= 4:
            level = 2
        # Рівень 3: ліфт >= 70, душ трап/піддон, пороги <= 3 см, вхід >= 5
        lift_ok3 = (self.lift_width_cm or 0) >= 70
        bath_ok3 = self.bathroom_type in (BathroomType.SHOWER_DRAIN, BathroomType.SHOWER_TRAY)
        thresh_ok3 = self.thresholds_max_height_cm is None or self.thresholds_max_height_cm <= 3
        if self.entrance_access >= 5 and lift_ok3 and bath_ok3 and thresh_ok3:
            level = 3
        # Рівень 4: ще краще — пороги до 2 см, вхід >= 7
        thresh_ok4 = self.thresholds_max_height_cm is None or self.thresholds_max_height_cm <= 2
        if (
            self.entrance_access >= 7
            and lift_ok3
            and bath_ok3
            and thresh_ok4
            and self.turning_radius_exists
        ):
            level = 4
        # Рівень 5: ліфт > 80, душ-трап, пороги <= 1, розворот, вхід >= 8
        lift_ok5 = (self.lift_width_cm or 0) > 80
        bath_ok5 = self.bathroom_type == BathroomType.SHOWER_DRAIN
        thresh_ok5 = (
            self.thresholds_max_height_cm is None or self.thresholds_max_height_cm <= 1
        ) or (self.thresholds_score or 0) >= 9
        if (
            self.entrance_access >= 8
            and lift_ok5
            and bath_ok5
            and thresh_ok5
            and self.turning_radius_exists
        ):
            level = 5
        return level

    def save(self, *args, **kwargs):
        if self.entrance_access is not None:
            self.entrance_status = self.get_status_from_score(self.entrance_access) or ""
        self.recalculate_total_score()
        super().save(*args, **kwargs)
        if self.property_id:
            self.property.mobility_level = self.compute_mobility_level()
            self.property.save(update_fields=["mobility_level"])


class ProfileReview(models.Model):
    """Відгук на користувача (профіль)."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="given_reviews",
        verbose_name="Автор відгуку",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_reviews",
        verbose_name="Оцінюваний користувач",
    )
    rating = models.PositiveSmallIntegerField(
        "Оцінка", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField("Відгук")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Відгук профілю"
        verbose_name_plural = "Відгуки профілів"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["author", "target_user"], name="unique_profile_review"
            ),
        ]

    def __str__(self):
        return f"Відгук {self.author.username} -> {self.target_user.username} ({self.rating}/5)"
