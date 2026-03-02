"""
Представлення платформи mobi home.
"""
import json
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q, Count

from .models import Property, AccessibilityAudit, BathroomType, EntranceStatus, ListingType, Feature, score_to_status
from .forms import AccessibilityAuditForm, RegisterForm, AddListingForm, PaymentForm
from .mobility import MOBILITY_LEVELS

# Координати міст для карти (приблизно)
CITY_COORDINATES = {
    'Київ': (50.4501, 30.5234),
    'Львів': (49.8397, 24.0297),
    'Одеса': (46.4825, 30.7233),
    'Дніпро': (48.4647, 35.0462),
    'Харків': (49.9935, 36.2304),
    'Запоріжжя': (47.8388, 35.1396),
    'Вінниця': (49.2328, 28.4681),
    'Чернівці': (48.2917, 25.9352),
    'Івано-Франківськ': (48.9226, 24.7111),
}

PROPERTIES_PER_PAGE = 9


def index(request):
    """Головна лендінг-сторінка: герой, статистика, обрані оголошення, CTA."""
    featured = Property.objects.filter(is_published=True).select_related('audit').order_by('-created_at')[:6]
    _assign_listing_photo_urls(featured)
    total_count = Property.objects.filter(is_published=True).count()
    cities_count = Property.objects.filter(is_published=True, city__isnull=False).exclude(city='').values('city').distinct().count()
    context = {
        'featured': featured,
        'total_count': total_count,
        'cities_count': cities_count,
    }
    return render(request, 'properties/index.html', context)


def about(request):
    """Сторінка «Про компанію»: місія, цінності, команда."""
    return render(request, 'properties/about.html')


def services(request):
    """Сторінка послуг."""
    return render(request, 'properties/services.html')


def faq(request):
    """Сторінку FAQ прибрано — редірект на головну (питання є в кінці головної)."""
    return redirect('properties:index')


def contact(request):
    """Контакти та форма зворотного зв'язку, карта."""
    if request.method == 'POST':
        messages.success(request, 'Дякуємо! Ваше повідомлення надіслано. Ми зв\'яжемося з вами найближчим часом.')
        return redirect('properties:contact')
    return render(request, 'properties/contact.html')


def home(request):
    """
    Головна: каталог квартир з фільтрами (тип, місто, ціна, кімнати, доступність), сортування, пагінація.
    """
    qs = Property.objects.filter(is_published=True).select_related('audit').prefetch_related('features')

    # Фільтр: тип оголошення (продаж / оренда)
    listing_type = request.GET.get('type', '').strip()
    if listing_type in ('sale', 'rent'):
        qs = qs.filter(listing_type=listing_type)

    # Фільтр: місто (точна відповідність, без дублікатів у списку)
    city = request.GET.get('city', '').strip()
    if city:
        qs = qs.filter(city=city)

    # Фільтр: ціна від / до
    try:
        price_min = request.GET.get('price_min')
        if price_min:
            qs = qs.filter(price__gte=float(price_min))
    except (TypeError, ValueError):
        pass
    try:
        price_max = request.GET.get('price_max')
        if price_max:
            qs = qs.filter(price__lte=float(price_max))
    except (TypeError, ValueError):
        pass

    # Фільтр: мінімум кімнат
    try:
        rooms = request.GET.get('rooms')
        if rooms:
            qs = qs.filter(rooms__gte=int(rooms))
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
    filter_lift = request.GET.get('lift_80') == '1'
    filter_shower = request.GET.get('shower_drain') == '1'
    filter_no_thresholds = request.GET.get('no_thresholds') == '1'
    if filter_lift or filter_shower or filter_no_thresholds:
        qs = qs.filter(has_audit)
        if filter_lift:
            qs = qs.filter(lift_ok)
        if filter_shower:
            qs = qs.filter(shower_drain)
        if filter_no_thresholds:
            qs = qs.filter(no_thresholds)

    # Фільтр: рівень мобільності (1–5) — житло, що задовольняє обраний рівень або вищий
    mobility = request.GET.get('mobility', '').strip()
    if mobility in ('1', '2', '3', '4', '5'):
        level = int(mobility)
        qs = qs.filter(mobility_level__isnull=False, mobility_level__gte=level)

    # Фільтр: зручності (фішки)
    feature_ids = request.GET.getlist('feature')
    if feature_ids:
        for fid in feature_ids:
            try:
                qs = qs.filter(features__id=int(fid))
            except (TypeError, ValueError):
                pass
        qs = qs.distinct()

    # Текстовий пошук
    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(address__icontains=query)
            | Q(city__icontains=query)
            | Q(description__icontains=query)
        )

    # Сортування
    sort = request.GET.get('sort', 'newest')
    if sort == 'price_asc':
        qs = qs.order_by('price')
    elif sort == 'price_desc':
        qs = qs.order_by('-price')
    elif sort == 'score':
        qs = qs.order_by('-audit__total_score')
    else:
        qs = qs.order_by('-created_at')

    total_count = qs.count()
    paginator = Paginator(qs, PROPERTIES_PER_PAGE)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(int(page_number))
    except (ValueError, TypeError):
        page_obj = paginator.page(1)
    _assign_listing_photo_urls(page_obj.object_list)

    # Список міст для фільтра (унікальні, відсортовані, без порожніх)
    cities = sorted(
        set(
            Property.objects.filter(is_published=True, city__isnull=False)
            .exclude(city='')
            .values_list('city', flat=True)
        )
    )

    # Усі зручності для фільтра
    all_features = Feature.objects.all().order_by('name')

    # Дані для карти: міста з кількістю оголошень та координатами
    city_counts = (
        Property.objects.filter(is_published=True, city__isnull=False)
        .exclude(city='')
        .values('city')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    map_cities = [
        {'city': c['city'], 'count': c['count'], 'lat': CITY_COORDINATES.get(c['city'], (50.45, 30.52))[0], 'lng': CITY_COORDINATES.get(c['city'], (50.45, 30.52))[1]}
        for c in city_counts
    ]
    map_cities_json = json.dumps(map_cities, ensure_ascii=False)

    context = {
        'properties': page_obj,
        'page_obj': page_obj,
        'query': query,
        'listing_type': listing_type,
        'city': city,
        'price_min': request.GET.get('price_min', ''),
        'price_max': request.GET.get('price_max', ''),
        'rooms': request.GET.get('rooms', ''),
        'filter_lift': filter_lift,
        'filter_shower': filter_shower,
        'filter_no_thresholds': filter_no_thresholds,
        'mobility': mobility,
        'mobility_levels': MOBILITY_LEVELS,
        'selected_features': [int(x) for x in feature_ids if x.isdigit()],
        'features': all_features,
        'sort': sort,
        'total_count': total_count,
        'cities': cities,
        'map_cities': map_cities,
        'map_cities_json': map_cities_json,
    }
    return render(request, 'properties/home.html', context)


def accessibility_levels(request):
    """Сторінка-довідник: який рівень мобільності для кого підходить."""
    context = {'mobility_levels': MOBILITY_LEVELS}
    return render(request, 'properties/accessibility_levels.html', context)


# Набір URL фото з інтернету для галереї оголошень (різні для кожного оголошення)
PROPERTY_PHOTO_URLS = [
    'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=1200',
    'https://images.unsplash.com/photo-1560185127-6a1896df2b2b?w=1200',
    'https://images.unsplash.com/photo-1600587644522-953f4752d2e5?w=1200',
    'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=1200',
    'https://images.unsplash.com/photo-1600573472592-401b489a3cdc?w=1200',
    'https://images.unsplash.com/photo-1600587644345-507b8c9d32e2?w=1200',
    'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=1200',
    'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=1200',
    'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=1200',
    'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=1200',
    'https://images.unsplash.com/photo-1600210962194-94d6f9102ec2?w=1200',
    'https://images.unsplash.com/photo-1484155274-0aad75c6e91e?w=1200',
    'https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?w=1200',
    'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1200',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1200',
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
    """Додає кожному оголошенню атрибут listing_photo_url (з інтернету за pk)."""
    n = len(PROPERTY_PHOTO_URLS)
    for p in properties:
        p.listing_photo_url = PROPERTY_PHOTO_URLS[p.pk % n]


def property_detail(request, pk):
    """Сторінка об'єкта: повна інформація та результати аудиту."""
    prop = get_object_or_404(Property.objects.prefetch_related('features'), pk=pk)
    audit = getattr(prop, 'audit', None)
    can_edit_audit = _can_manage_property(request.user, prop) if request.user.is_authenticated else False
    property_photos = _property_photos_for_pk(prop.pk)

    rows = []
    if audit:
        status_choices = dict(EntranceStatus.choices)

        def get_status_display(score):
            if score is None:
                return '—'
            k = score_to_status(score)
            return status_choices.get(k, k or '—')

        rows = [
            ('Вхід', audit.entrance_access, get_status_display(audit.entrance_access), audit.entrance_comment),
            ('Ліфт (ширина см)', audit.lift_width_cm, f'{audit.lift_score}/10' if audit.lift_score is not None else '—', audit.lift_comment),
            ('Статус ліфта', audit.lift_score, get_status_display(audit.lift_score), ''),
            ('Тип санвузлу', audit.get_bathroom_type_display() if audit.bathroom_type else '—', '—', audit.bathroom_comment),
            ('Пороги (макс. см)', audit.thresholds_max_height_cm, get_status_display(audit.thresholds_score), audit.thresholds_comment),
            ('Статус порогів', audit.thresholds_score, get_status_display(audit.thresholds_score), ''),
            ('Радіус для розвороту', 'Так' if audit.turning_radius_exists else 'Ні', '—', audit.turning_comment),
        ]

    context = {
        'property': prop,
        'audit': audit,
        'audit_rows': rows,
        'can_edit_audit': can_edit_audit,
        'property_photos': property_photos,
    }
    return render(request, 'properties/property_detail.html', context)


def _can_manage_property(user, prop):
    """Чи може користувач редагувати/видаляти оголошення (власник або адмін)."""
    if not user.is_authenticated:
        return False
    return user.is_staff or (getattr(prop, 'owner_id', None) and prop.owner_id == user.id)


@login_required(login_url='/login/')
def delete_property(request, pk):
    """Видалення оголошення. Доступно лише власнику або адміну."""
    prop = get_object_or_404(Property, pk=pk)
    if not _can_manage_property(request.user, prop):
        messages.error(request, 'Видаляти оголошення можуть лише його власник або адміністратор.')
        return redirect('properties:property_detail', pk=pk)
    if request.method == 'POST':
        name = prop.name
        prop.delete()
        messages.success(request, f'Оголошення «{name}» видалено.')
        return redirect('properties:home')
    return render(request, 'properties/property_confirm_delete.html', {'property': prop})


def auditor_form(request, pk=None):
    """Форма аудитора для додавання/редагування результатів перевірки."""
    if pk:
        prop = get_object_or_404(Property, pk=pk)
        audit = getattr(prop, 'audit', None)
        if not audit:
            audit = AccessibilityAudit(property=prop)
    else:
        prop = None
        audit = None

    if request.method == 'POST':
        form = AccessibilityAuditForm(request.POST, instance=audit)
        if form.is_valid():
            obj = form.save(commit=False)
            if not obj.property_id:
                prop_id = request.POST.get('property')
                if prop_id:
                    obj.property_id = int(prop_id)
                    obj.save()
                    return redirect('properties:property_detail', pk=obj.property_id)
                form.add_error(None, 'Оберіть об\'єкт нерухомості.')
            else:
                obj.save()
                return redirect('properties:property_detail', pk=obj.property_id)
    else:
        form = AccessibilityAuditForm(instance=audit)

    context = {
        'form': form,
        'property': prop,
        'audit': audit,
        'properties_list': Property.objects.filter(is_published=True).order_by('-created_at') if not prop else None,
    }
    return render(request, 'properties/auditor_form.html', context)


def register(request):
    """Реєстрація. Після успіху — редірект на додати оголошення."""
    if request.user.is_authenticated:
        return redirect('properties:add_listing')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Реєстрація успішна. Додайте ваше оголошення.')
            return redirect('properties:add_listing')
        else:
            messages.error(request, 'Виправте помилки у формі.')
    else:
        form = RegisterForm()
    return render(request, 'properties/register.html', {'form': form})


def login_view(request):
    """Вхід за логіном (ім'я користувача) та паролем. Після успіху — редірект на add_listing або next."""
    if request.user.is_authenticated:
        return redirect('properties:add_listing')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Ви успішно увійшли.')
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('properties:add_listing')
        else:
            messages.error(request, 'Невірний логін або пароль. Спробуйте ще раз.')
    else:
        form = AuthenticationForm(request)
    form.fields['username'].label = "Ім'я користувача"
    form.fields['password'].label = 'Пароль'
    form.fields['username'].widget.attrs.update({'class': 'form-control form-control-sm', 'placeholder': "Ім'я користувача (логін)", 'autocomplete': 'username'})
    form.fields['password'].widget.attrs.update({'class': 'form-control form-control-sm', 'placeholder': 'Пароль', 'autocomplete': 'current-password'})
    return render(request, 'properties/login.html', {'form': form})


@login_required(login_url='/login/')
def add_listing(request):
    """Форма додавання оголошення (всі поля + рівні доступності). Після збереження — редірект на оплату."""
    if request.method == 'POST':
        form = AddListingForm(request.POST, request.FILES)
        if form.is_valid():
            prop = form.save(commit=False)
            prop.owner = request.user
            prop.save()
            form.save_m2m()
            messages.success(request, 'Оголошення збережено. Перейдіть до оплати для публікації.')
            return redirect('properties:payment', pk=prop.pk)
        else:
            messages.error(request, 'Виправте помилки у формі.')
    else:
        form = AddListingForm()
    return render(request, 'properties/add_listing.html', {'form': form})


def logout_view(request):
    """Вихід з облікового запису. Редірект на головну."""
    logout(request)
    messages.info(request, 'Ви вийшли з облікового запису.')
    return redirect('properties:index')


def payment(request, pk):
    """Оплата банківською карткою (мок). Після успіху — публікація оголошення та редірект. Доступно лише власнику або адміну."""
    prop = get_object_or_404(Property, pk=pk)
    if not request.user.is_authenticated:
        messages.error(request, 'Увійдіть, щоб оплатити оголошення.')
        return redirect('properties:property_detail', pk=pk)
    if not (request.user.is_staff or (getattr(prop, 'owner_id', None) and prop.owner_id == request.user.id)):
        messages.error(request, 'Редагувати та оплачувати можна лише своє оголошення.')
        return redirect('properties:property_detail', pk=pk)
    if prop.is_published:
        messages.info(request, 'Оголошення вже опубліковане.')
        return redirect('properties:property_detail', pk=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            prop.is_published = True
            prop.save()
            messages.success(request, 'Оплата пройшла успішно. Ваше оголошення опубліковано.')
            return redirect('properties:property_detail', pk=pk)
        else:
            messages.error(request, 'Перевірте дані картки.')
    else:
        form = PaymentForm()
    return render(request, 'properties/payment.html', {'form': form, 'property': prop})
