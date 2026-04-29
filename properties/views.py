"""
Представлення платформи mobi home.
"""

import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.db.models import Avg, Case, Count, IntegerField, Q, Value, When
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import AccessibilityAuditForm, AddListingForm, PaymentForm, RegisterForm, UserProfileForm, ReviewForm
from .mobility import MOBILITY_LEVELS
from .models import (
    AccessibilityAudit,
    BathroomType,
    EntranceStatus,
    Feature,
    ListingType,
    Property,
    PropertyFavorite,
    PropertyPhoto,
    ProfileReview,
    score_to_status,
)

# Координати міст для карти (приблизно)
CITY_COORDINATES = {
    "Київ": (50.4501, 30.5234),
    "Львів": (49.8397, 24.0297),
    "Одеса": (46.4825, 30.7233),
    "Дніпро": (48.4647, 35.0462),
    "Харків": (49.9935, 36.2304),
    "Запоріжжя": (47.8388, 35.1396),
    "Вінниця": (49.2328, 28.4681),
    "Чернівці": (48.2917, 25.9352),
    "Івано-Франківськ": (48.9226, 24.7111),
    "Долобів": (49.6365, 23.4728),
}

PROPERTIES_PER_PAGE = 9


def index(request):
    """Головна лендінг-сторінка: герой, статистика, обрані оголошення, CTA."""
    now_index = timezone.now()
    featured = (
        Property.objects.filter(is_published=True)
        .select_related("audit")
        .prefetch_related("extra_photos")
        .annotate(
            featured_active=Case(
                When(
                    Q(is_featured=True)
                    & (Q(featured_until__isnull=True) | Q(featured_until__gt=now_index)),
                    then=Value(1),
                ),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("-featured_active", "-created_at")[:6]
    )
    _assign_listing_photo_urls(featured)
    total_count = Property.objects.filter(is_published=True).count()
    cities_count = (
        Property.objects.filter(is_published=True, city__isnull=False)
        .exclude(city="")
        .values("city")
        .distinct()
        .count()
    )
    context = {
        "featured": featured,
        "total_count": total_count,
        "cities_count": cities_count,
    }
    return render(request, "properties/index.html", context)


def about(request):
    """Сторінка «Про компанію»: місія, цінності, команда."""
    return render(request, "properties/about.html")


def services(request):
    """Сторінка послуг."""
    return render(request, "properties/services.html")


def faq(request):
    """Сторінку FAQ прибрано — редірект на головну (питання є в кінці головної)."""
    return redirect("properties:index")


def contact(request):
    """Контакти та форма зворотного зв'язку, карта."""
    if request.method == "POST":
        messages.success(
            request, "Дякуємо! Ваше повідомлення надіслано. Ми зв'яжемося з вами найближчим часом."
        )
        return redirect("properties:contact")
    return render(request, "properties/contact.html")


def privacy_policy(request):
    """Сторінка політики конфіденційності."""
    return render(request, "properties/privacy_policy.html")


def terms_of_service(request):
    """Сторінка правил сервісу."""
    return render(request, "properties/terms_of_service.html")


def home(request):
    """
    Головна: каталог квартир з фільтрами (тип, місто, ціна, кімнати, доступність), сортування, пагінація.
    """
    qs = (
        Property.objects.filter(is_published=True)
        .select_related("audit")
        .prefetch_related("features", "extra_photos")
    )

    # Фільтр: тип оголошення (продаж / оренда)
    listing_type = request.GET.get("type", "").strip()
    if listing_type in ("sale", "rent"):
        qs = qs.filter(listing_type=listing_type)

    # Фільтр: місто (точна відповідність, без дублікатів у списку)
    city = request.GET.get("city", "").strip()
    if city:
        qs = qs.filter(city=city)

    # Фільтр: ціна від / до
    try:
        price_min = request.GET.get("price_min")
        if price_min:
            qs = qs.filter(price__gte=float(price_min))
    except (TypeError, ValueError):
        pass
    try:
        price_max = request.GET.get("price_max")
        if price_max:
            qs = qs.filter(price__lte=float(price_max))
    except (TypeError, ValueError):
        pass

    # Фільтр: мінімум кімнат
    try:
        rooms = request.GET.get("rooms")
        if rooms:
            qs = qs.filter(rooms__gte=int(rooms))
    except (TypeError, ValueError):
        pass

    # Фільтр: максимум кімнат
    try:
        rooms_max = request.GET.get("rooms_max")
        if rooms_max:
            qs = qs.filter(rooms__lte=int(rooms_max))
    except (TypeError, ValueError):
        pass

    # Фільтр: площа від / до (м²)
    try:
        area_min = request.GET.get("area_min")
        if area_min:
            qs = qs.filter(area_sqm__gte=float(area_min))
    except (TypeError, ValueError):
        pass
    try:
        area_max = request.GET.get("area_max")
        if area_max:
            qs = qs.filter(area_sqm__lte=float(area_max))
    except (TypeError, ValueError):
        pass

    # Критичні точки доступності
    has_audit = Q(audit__isnull=False)
    lift_ok = Q(audit__lift_width_cm__gt=80)
    shower_drain = Q(audit__bathroom_type=BathroomType.SHOWER_DRAIN)
    no_thresholds = (
        Q(audit__thresholds_max_height_cm__lte=2)
        | Q(audit__thresholds_max_height_cm__isnull=True)
        | Q(audit__thresholds_score__gte=9)
    )
    filter_lift = request.GET.get("lift_80") == "1"
    filter_shower = request.GET.get("shower_drain") == "1"
    filter_no_thresholds = request.GET.get("no_thresholds") == "1"
    if filter_lift or filter_shower or filter_no_thresholds:
        qs = qs.filter(has_audit)
        if filter_lift:
            qs = qs.filter(lift_ok)
        if filter_shower:
            qs = qs.filter(shower_drain)
        if filter_no_thresholds:
            qs = qs.filter(no_thresholds)

    # Фільтр: радіус для розвороту (мобільність)
    filter_turning = request.GET.get("turning_radius") == "1"
    if filter_turning:
        qs = qs.filter(has_audit, audit__turning_radius_exists=True)

    # Фільтр: тип санвузлу (мобільність)
    bathroom_type = request.GET.get("bathroom_type", "").strip()
    if bathroom_type in ("bath", "shower_tray", "shower_drain"):
        qs = qs.filter(has_audit, audit__bathroom_type=bathroom_type)

    # Фільтр: лише з проведеним аудитом
    filter_has_audit = request.GET.get("has_audit") == "1"
    if filter_has_audit:
        qs = qs.filter(has_audit)

    # Фільтр: мінімальний бал аудиту (1–10)
    audit_score_min_val = request.GET.get("audit_score_min", "").strip()
    try:
        if audit_score_min_val:
            score = float(audit_score_min_val)
            if 1 <= score <= 10:
                qs = qs.filter(has_audit, audit__total_score__gte=score)
    except (TypeError, ValueError):
        audit_score_min_val = ""

    # Фільтр: лише перевірені оголошення
    filter_verified = request.GET.get("verified") == "1"
    if filter_verified:
        qs = qs.filter(is_verified=True)

    # Фільтр: рівень мобільності (1–5) — житло, що задовольняє обраний рівень або вищий
    mobility = request.GET.get("mobility", "").strip()
    if mobility in ("1", "2", "3", "4", "5"):
        level = int(mobility)
        qs = qs.filter(mobility_level__isnull=False, mobility_level__gte=level)

    # Фільтр: зручності (фішки)
    feature_ids = request.GET.getlist("feature")
    if feature_ids:
        for fid in feature_ids:
            try:
                qs = qs.filter(features__id=int(fid))
            except (TypeError, ValueError):
                pass
        qs = qs.distinct()

    # Текстовий пошук
    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(address__icontains=query)
            | Q(city__icontains=query)
            | Q(description__icontains=query)
        )

    # Сортування (реклама: лише з активною featured_until)
    now = timezone.now()
    qs = qs.annotate(
        featured_active=Case(
            When(
                Q(is_featured=True) & (Q(featured_until__isnull=True) | Q(featured_until__gt=now)),
                then=Value(1),
            ),
            default=Value(0),
            output_field=IntegerField(),
        )
    )
    sort = request.GET.get("sort", "newest")
    if sort == "price_asc":
        qs = qs.order_by("price")
    elif sort == "price_desc":
        qs = qs.order_by("-price")
    elif sort == "score":
        qs = qs.order_by("-audit__total_score")
    else:
        qs = qs.order_by("-featured_active", "-created_at")

    total_count = qs.count()
    paginator = Paginator(qs, PROPERTIES_PER_PAGE)
    page_number = request.GET.get("page", 1)
    try:
        page_obj = paginator.page(int(page_number))
    except (ValueError, TypeError):
        page_obj = paginator.page(1)
    _assign_listing_photo_urls(page_obj.object_list)

    # Список міст для фільтра (унікальні, відсортовані, нормалізовані)
    cities = sorted(
        set(
            (c or "").strip()
            for c in Property.objects.filter(is_published=True, city__isnull=False)
            .exclude(city="")
            .values_list("city", flat=True)
            if (c or "").strip()
        )
    )

    # Усі зручності для фільтра
    all_features = Feature.objects.all().order_by("name")

    # Дані для карти: при виборі міста показуємо лише його, інакше — усі міста з оголошеннями
    city_counts = (
        Property.objects.filter(is_published=True, city__isnull=False)
        .exclude(city="")
        .values("city")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    all_map_cities = []
    for c in city_counts:
        city_name = (c["city"] or "").strip()
        if not city_name:
            continue
        coords = CITY_COORDINATES.get(city_name, (50.45, 30.52))
        all_map_cities.append(
            {
                "city": city_name,
                "count": c["count"],
                "lat": coords[0],
                "lng": coords[1],
            }
        )
    if city:
        map_cities = [m for m in all_map_cities if m["city"] == city]
        if map_cities:
            map_center = (map_cities[0]["lat"], map_cities[0]["lng"])
            map_zoom = 11
        else:
            map_cities = all_map_cities
            map_center = (49.0, 32.0)
            map_zoom = 6
    else:
        map_cities = all_map_cities
        map_center = (49.0, 32.0)
        map_zoom = 6
    map_cities_json = json.dumps(map_cities, ensure_ascii=False)
    map_center_json = json.dumps(map_center)

    context = {
        "properties": page_obj,
        "page_obj": page_obj,
        "query": query,
        "listing_type": listing_type,
        "city": city,
        "price_min": request.GET.get("price_min", ""),
        "price_max": request.GET.get("price_max", ""),
        "rooms": request.GET.get("rooms", ""),
        "rooms_max": request.GET.get("rooms_max", ""),
        "area_min": request.GET.get("area_min", ""),
        "area_max": request.GET.get("area_max", ""),
        "filter_lift": filter_lift,
        "filter_shower": filter_shower,
        "filter_no_thresholds": filter_no_thresholds,
        "filter_turning": filter_turning,
        "bathroom_type": bathroom_type,
        "filter_has_audit": filter_has_audit,
        "audit_score_min": audit_score_min_val,
        "filter_verified": filter_verified,
        "bathroom_type_choices": BathroomType.choices,
        "mobility": mobility,
        "mobility_levels": MOBILITY_LEVELS,
        "selected_features": [int(x) for x in feature_ids if x.isdigit()],
        "features": all_features,
        "sort": sort,
        "total_count": total_count,
        "cities": cities,
        "map_cities": map_cities,
        "map_cities_json": map_cities_json,
        "map_center": map_center,
        "map_center_json": map_center_json,
        "map_zoom": map_zoom,
    }
    return render(request, "properties/home.html", context)


def accessibility_levels(request):
    """Сторінка-довідник: який рівень мобільності для кого підходить."""
    context = {"mobility_levels": MOBILITY_LEVELS}
    return render(request, "properties/accessibility_levels.html", context)


# Набір URL фото з інтернету для галереї оголошень (різні для кожного оголошення)
PROPERTY_PHOTO_URLS = [
    "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=1200",
    "https://images.unsplash.com/photo-1560185127-6a1896df2b2b?w=1200",
    "https://images.unsplash.com/photo-1600587644522-953f4752d2e5?w=1200",
    "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=1200",
    "https://images.unsplash.com/photo-1600573472592-401b489a3cdc?w=1200",
    "https://images.unsplash.com/photo-1600587644345-507b8c9d32e2?w=1200",
    "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=1200",
    "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=1200",
    "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=1200",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=1200",
    "https://images.unsplash.com/photo-1600210962194-94d6f9102ec2?w=1200",
    "https://images.unsplash.com/photo-1484155274-0aad75c6e91e?w=1200",
    "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?w=1200",
    "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1200",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1200",
]


def _property_photos_for_pk(pk):
    """Повертає 3 різні URL фото для оголошення з заданим pk."""
    n = len(PROPERTY_PHOTO_URLS)
    return [
        PROPERTY_PHOTO_URLS[pk % n],
        PROPERTY_PHOTO_URLS[(pk + 1) % n],
        PROPERTY_PHOTO_URLS[(pk + 2) % n],
    ]


def _assign_listing_photo_urls(properties):
    """Додає кожному оголошенню атрибут listing_photo_url: своє фото, додаткове фото або placeholder."""
    n = len(PROPERTY_PHOTO_URLS)
    for p in properties:
        if p.photo:
            p.listing_photo_url = p.photo.url
        else:
            extras = getattr(p, "extra_photos", None)
            extras_list = list(extras.all()) if extras else []
            first_extra = extras_list[0] if extras_list else None
            p.listing_photo_url = (
                first_extra.image.url if first_extra else PROPERTY_PHOTO_URLS[p.pk % n]
            )


def property_detail(request, pk):
    """Сторінка об'єкта: повна інформація та результати аудиту. Фото: головне + додаткові; якщо немає — placeholder."""
    prop = get_object_or_404(Property.objects.prefetch_related("features", "extra_photos"), pk=pk)
    audit = getattr(prop, "audit", None)
    can_edit_audit = (
        _can_manage_property(request.user, prop) if request.user.is_authenticated else False
    )
    # Лічильник переглядів: один раз за сесію на оголошення
    session_key = "viewed_property_%s" % pk
    if not request.session.get(session_key):
        prop.view_count = (prop.view_count or 0) + 1
        prop.save(update_fields=["view_count"])
        request.session[session_key] = True
    property_photos = []
    if prop.photo:
        property_photos.append(prop.photo.url)
    property_photos.extend(p.image.url for p in prop.extra_photos.all())
    if not property_photos:
        property_photos = _property_photos_for_pk(prop.pk)

    now = timezone.now()
    can_promote = (
        can_edit_audit
        and prop.is_published
        and (not prop.is_featured or (prop.featured_until and prop.featured_until < now))
    )
    featured_until_display = (
        prop.featured_until if prop.featured_until and prop.featured_until > now else None
    )

    rows = []
    if audit:
        status_choices = dict(EntranceStatus.choices)

        def get_status_display(score):
            if score is None:
                return "—"
            k = score_to_status(score)
            return status_choices.get(k, k or "—")

        rows = [
            (
                "Вхід до будинку (пандус, сходи)",
                f"{audit.entrance_access}/10" if audit.entrance_access else "—",
                get_status_display(audit.entrance_access),
                audit.entrance_comment,
            ),
            (
                "Ширина дверного прорізу ліфта",
                f"{audit.lift_width_cm} см" if audit.lift_width_cm else "—",
                get_status_display(audit.lift_score),
                audit.lift_comment,
            ),
            (
                "Зручність санвузлу",
                audit.get_bathroom_type_display() if audit.bathroom_type else "—",
                "Ідеально" if audit.bathroom_type == BathroomType.SHOWER_DRAIN else ("Потребує покращення" if audit.bathroom_type else "—"),
                audit.bathroom_comment,
            ),
            (
                "Висота порогів у приміщенні",
                f"{audit.thresholds_max_height_cm} см" if audit.thresholds_max_height_cm is not None else "—",
                get_status_display(audit.thresholds_score),
                audit.thresholds_comment,
            ),
            (
                "Простір для розвороту на візку",
                "Достатньо" if audit.turning_radius_exists else "Обмежений",
                "Ідеально" if audit.turning_radius_exists else "Важкодоступно",
                audit.turning_comment,
            ),
        ]

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = PropertyFavorite.objects.filter(user=request.user, property=prop).exists()

    context = {
        "property": prop,
        "audit": audit,
        "audit_rows": rows,
        "can_edit_audit": can_edit_audit,
        "property_photos": property_photos,
        "can_promote": can_promote,
        "featured_until_display": featured_until_display,
        "is_favorite": is_favorite,
    }
    return render(request, "properties/property_detail.html", context)


def _can_manage_property(user, prop):
    """Чи може користувач редагувати/видаляти оголошення (власник або адмін)."""
    if not user.is_authenticated:
        return False
    return user.is_staff or (getattr(prop, "owner_id", None) and prop.owner_id == user.id)


@login_required(login_url="/auth/")
def delete_property(request, pk):
    """Видалення оголошення. Доступно лише власнику або адміну."""
    prop = get_object_or_404(Property, pk=pk)
    if not _can_manage_property(request.user, prop):
        messages.error(request, "Видаляти оголошення можуть лише його власник або адміністратор.")
        return redirect("properties:property_detail", pk=pk)
    if request.method == "POST":
        name = prop.name
        prop.delete()
        messages.success(request, f"Оголошення «{name}» видалено.")
        return redirect("properties:home")
    return render(request, "properties/property_confirm_delete.html", {"property": prop})


@login_required(login_url="/auth/")
def auditor_form(request, pk=None):
    """Форма аудитора для додавання/редагування результатів перевірки."""
    if not request.user.is_staff:
        messages.error(request, "Форму аудиту може заповнювати тільки адміністратор.")
        if pk:
            return redirect("properties:property_detail", pk=pk)
        return redirect("properties:home")

    if pk:
        prop = get_object_or_404(Property, pk=pk)
        audit = getattr(prop, "audit", None)
        if not audit:
            audit = AccessibilityAudit(property=prop)
    else:
        prop = None
        audit = None

    if request.method == "POST":
        form = AccessibilityAuditForm(request.POST, instance=audit)
        if form.is_valid():
            obj = form.save(commit=False)
            if not obj.property_id:
                prop_id = request.POST.get("property")
                if prop_id:
                    obj.property_id = int(prop_id)
                    obj.save()
                    return redirect("properties:property_detail", pk=obj.property_id)
                form.add_error(None, "Оберіть об'єкт нерухомості.")
            else:
                obj.save()
                return redirect("properties:property_detail", pk=obj.property_id)
    else:
        form = AccessibilityAuditForm(instance=audit)

    context = {
        "form": form,
        "property": prop,
        "audit": audit,
        "properties_list": (
            Property.objects.filter(is_published=True).order_by("-created_at") if not prop else None
        ),
    }
    return render(request, "properties/auditor_form.html", context)


def _prepare_login_form(form):
    form.fields["username"].label = "Ім'я користувача"
    form.fields["password"].label = "Пароль"
    form.fields["username"].widget.attrs.update(
        {
            "class": "form-control",
            "placeholder": "Телефон або e-mail / логін",
            "autocomplete": "username",
        }
    )
    form.fields["password"].widget.attrs.update(
        {"class": "form-control", "placeholder": "Пароль", "autocomplete": "current-password"}
    )


def auth_page(request):
    """Об'єднана сторінка: Вхід та Реєстрація на одній сторінці (таби)."""
    if request.user.is_authenticated:
        return redirect("properties:add_listing")
    next_url = (request.GET.get("next") or request.POST.get("next") or "")[:500]
    active_tab = request.GET.get("tab", "login")
    login_form = AuthenticationForm(request)
    register_form = RegisterForm()
    if request.method == "POST":
        form_type = request.POST.get("form_type", "login")
        next_url = request.POST.get("next", next_url)
        if form_type == "register":
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                messages.success(request, "Реєстрація успішна. Додайте ваше оголошення.")
                return redirect(next_url if next_url.startswith("/") else "properties:add_listing")
            messages.error(request, "Виправте помилки у формі реєстрації.")
            active_tab = "register"
        else:
            login_form = AuthenticationForm(request, data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                if request.POST.get("remember_me"):
                    request.session.set_expiry(60 * 60 * 24 * 14)
                else:
                    request.session.set_expiry(0)
                messages.success(request, "Ви успішно увійшли.")
                return redirect(next_url if next_url.startswith("/") else "properties:add_listing")
            messages.error(request, "Невірний логін або пароль.")
            active_tab = "login"
    _prepare_login_form(login_form)
    return render(
        request,
        "properties/auth.html",
        {
            "login_form": login_form,
            "register_form": register_form,
            "active_tab": active_tab,
            "next_url": next_url,
        },
    )


def coming_soon(request):
    """Сторінка «Скоро» для соціального входу (Google, Telegram, Дія)."""
    return render(request, "properties/coming_soon.html")


def register(request):
    """Редірект на об'єднану сторінку входу/реєстрації."""
    if request.user.is_authenticated:
        return redirect("properties:add_listing")
    next_url = request.GET.get("next", "")
    url = reverse("properties:auth")
    if next_url:
        return redirect(f"{url}?tab=register&next={next_url}")
    return redirect(f"{url}?tab=register")


def login_view(request):
    """Редірект на об'єднану сторінку входу/реєстрації."""
    if request.user.is_authenticated:
        return redirect("properties:add_listing")
    qs = request.GET.urlencode()
    url = reverse("properties:auth")
    return redirect(f"{url}?{qs}" if qs else url)


@login_required(login_url="/auth/")
def add_listing(request):
    """Форма додавання оголошення (всі поля + рівні доступності). Після збереження — редірект на оплату."""
    if request.method == "POST":
        form = AddListingForm(request.POST, request.FILES)
        if form.is_valid():
            prop = form.save(commit=False)
            prop.owner = request.user
            prop.save()
            form.save_m2m()
            for i, f in enumerate(request.FILES.getlist("extra_photos")):
                if f:
                    PropertyPhoto.objects.create(property=prop, image=f, order=i)
            messages.success(request, "Оголошення збережено. Оберіть спосіб публікації.")
            return redirect("properties:payment", pk=prop.pk)
        else:
            messages.error(request, "Виправте помилки у формі.")
    else:
        form = AddListingForm()
        
    # Групування зручностей для шаблону
    from .models import Feature
    features = Feature.objects.all().order_by('category', 'name')
    raw_groups = {}
    for feature in features:
        cat = feature.category or 'other'
        if cat not in raw_groups:
            raw_groups[cat] = []
        raw_groups[cat].append(feature)
        
    ordered_groups = []
    category_names = {
        'apartment': 'В квартирі',
        'building': 'В будинку та на території',
        'rules': 'Правила проживання',
    }
    for cat_key in ['apartment', 'building', 'rules', 'other']:
        if cat_key in raw_groups:
            ordered_groups.append({
                'name': category_names.get(cat_key, 'Інше'),
                'features': raw_groups[cat_key]
            })
            
    # Список вибраних зручностей (для збереження стану при помилках валідації)
    checked_features = form['features'].value() or []
    checked_features = [str(x) for x in checked_features]

    context = {
        "form": form,
        "grouped_features": ordered_groups,
        "checked_features": checked_features,
    }
    return render(request, "properties/add_listing.html", context)


def logout_view(request):
    """Вихід з облікового запису. Приймає GET і POST, редірект на головну."""
    logout(request)
    messages.info(request, "Ви вийшли з облікового запису.")
    return redirect("properties:index")


def toggle_favorite(request, pk):
    """Додати або прибрати оголошення з обраного. POST; повертає JSON { is_favorite: bool }."""
    if not request.user.is_authenticated:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accepts(
            "application/json"
        ):
            return JsonResponse({"error": "login_required"}, status=401)
        from urllib.parse import urlencode

        return redirect(
            reverse("properties:auth") + "?" + urlencode({"next": request.build_absolute_uri()})
        )

    prop = get_object_or_404(Property, pk=pk)
    fav, created = PropertyFavorite.objects.get_or_create(user=request.user, property=prop)
    if not created:
        fav.delete()
        is_favorite = False
    else:
        is_favorite = True
    return JsonResponse({"is_favorite": is_favorite})


@login_required(login_url="/auth/")
def profile(request):
    """Сторінка профілю: дані користувача, його оголошення та обрані."""
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Профіль оновлено.")
            return redirect("properties:profile")
    else:
        form = UserProfileForm(instance=request.user)

    user_listings = Property.objects.filter(owner=request.user).order_by("-created_at")
    favorite_listings = (
        Property.objects.filter(favorited_by__user=request.user)
        .order_by("-favorited_by__created_at")
        .distinct()
    )
    
    reviews = ProfileReview.objects.filter(target_user=request.user)
    avg_rating = reviews.aggregate(Avg("rating"))["rating__avg"]

    context = {
        "user_listings": user_listings, 
        "favorite_listings": favorite_listings,
        "form": form,
        "reviews": reviews,
        "avg_rating": avg_rating,
    }
    return render(request, "properties/profile.html", context)


def public_profile(request, username):
    """Публічний профіль користувача для перегляду та оцінки."""
    target_user = get_object_or_404(User, username=username)
    user_listings = Property.objects.filter(owner=target_user, is_published=True).order_by("-created_at")
    reviews = ProfileReview.objects.filter(target_user=target_user)
    avg_rating = reviews.aggregate(Avg("rating"))["rating__avg"]

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Увійдіть, щоб залишити відгук.")
            return redirect("properties:public_profile", username=username)
        if request.user == target_user:
            messages.error(request, "Ви не можете оцінювати самі себе.")
            return redirect("properties:public_profile", username=username)
            
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.author = request.user
            review.target_user = target_user
            existing = ProfileReview.objects.filter(author=request.user, target_user=target_user).first()
            if existing:
                existing.rating = review.rating
                existing.text = review.text
                existing.save()
                messages.success(request, "Ваш відгук оновлено.")
            else:
                review.save()
                messages.success(request, "Ваш відгук додано.")
            return redirect("properties:public_profile", username=username)
    else:
        form = ReviewForm()

    context = {
        "target_user": target_user,
        "user_listings": user_listings,
        "reviews": reviews,
        "avg_rating": avg_rating,
        "form": form,
    }
    return render(request, "properties/public_profile.html", context)


def payment(request, pk):
    """Публікація оголошення: безкоштовно або оплата (LiqPay/Stripe). Доступно лише власнику або адміну."""
    prop = get_object_or_404(Property, pk=pk)
    if not request.user.is_authenticated:
        messages.error(request, "Увійдіть, щоб опублікувати оголошення.")
        return redirect("properties:property_detail", pk=pk)
    if not (
        request.user.is_staff
        or (getattr(prop, "owner_id", None) and prop.owner_id == request.user.id)
    ):
        messages.error(request, "Публікувати можна лише своє оголошення.")
        return redirect("properties:property_detail", pk=pk)
    if prop.is_published:
        messages.info(request, "Оголошення вже опубліковане.")
        return redirect("properties:property_detail", pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "free":
            prop.is_published = True
            prop.is_featured = False
            prop.featured_until = None
            prop.save(update_fields=["is_published", "is_featured", "featured_until"])
            messages.success(
                request, "Оголошення опубліковано безкоштовно. Пізніше можна замовити рекламу."
            )
            return redirect("properties:property_detail", pk=pk)
    return render(request, "properties/payment.html", {"property": prop})


def promote_listing(request, pk):
    """Рекламувати вже опубліковане оголошення (підвищена видимість 30 днів)."""
    prop = get_object_or_404(Property, pk=pk)
    if not request.user.is_authenticated:
        messages.error(request, "Увійдіть, щоб замовити рекламу.")
        return redirect("properties:property_detail", pk=pk)
    if not (
        request.user.is_staff
        or (getattr(prop, "owner_id", None) and prop.owner_id == request.user.id)
    ):
        messages.error(request, "Рекламувати можна лише своє оголошення.")
        return redirect("properties:property_detail", pk=pk)
    if not prop.is_published:
        messages.error(request, "Спочатку опублікуйте оголошення.")
        return redirect("properties:property_detail", pk=pk)
    FEATURED_PRICE = 99
    PROMOTE_DAYS = 30
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            now = timezone.now()
            if prop.featured_until and prop.featured_until > now:
                prop.featured_until = prop.featured_until + timedelta(days=PROMOTE_DAYS)
            else:
                prop.featured_until = now + timedelta(days=PROMOTE_DAYS)
            prop.is_featured = True
            prop.save(update_fields=["is_featured", "featured_until"])
            messages.success(
                request,
                f'Реклама активована на {PROMOTE_DAYS} днів. Діє до {prop.featured_until.strftime("%d.%m.%Y")}.',
            )
            return redirect("properties:property_detail", pk=pk)
        messages.error(request, "Перевірте дані картки.")
    else:
        form = PaymentForm()
    return render(
        request,
        "properties/promote_listing.html",
        {"property": prop, "featured_price": FEATURED_PRICE, "form": form},
    )


def payment_paid(request, pk):
    """Оплата підвищеної видимості. Форма картки, після валідації — публікація з is_featured=True."""
    prop = get_object_or_404(Property, pk=pk)
    if not request.user.is_authenticated:
        messages.error(request, "Увійдіть, щоб оплатити.")
        return redirect("properties:property_detail", pk=pk)
    property_detail_url = (
        reverse("properties:property_detail", kwargs={"pk": pk}) + "#propertyContact"
    )
    FEATURED_PRICE = 99
    if request.method == "POST":
        now = timezone.now()
        promo_days = 30
        # Після оплати даємо оголошенню підвищену видимість (а користувача перекидаємо до контактів продавця).
        if prop.featured_until and prop.featured_until > now:
            prop.featured_until = prop.featured_until + timedelta(days=promo_days)
        else:
            prop.featured_until = now + timedelta(days=promo_days)
        prop.is_published = True
        prop.is_featured = True
        prop.save(update_fields=["is_published", "is_featured", "featured_until"])
        messages.success(
            request, f"Оплата {FEATURED_PRICE} грн через PayPal прийнята. Доступ до контактів надається."
        )
        return redirect(property_detail_url)

    return render(
        request,
        "properties/payment_paid.html",
        {"property": prop, "featured_price": FEATURED_PRICE},
    )
