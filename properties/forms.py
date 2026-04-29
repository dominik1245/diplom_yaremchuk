"""
Форми для аудиту, реєстрації, додавання оголошень та оплати.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .mobility import MOBILITY_LEVELS
from .models import AccessibilityAudit, Feature, Property


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control form-control-sm", "placeholder": "email@example.com"}
        ),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control form-control-sm", "placeholder": "Логін"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control form-control-sm", "placeholder": "Пароль"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control form-control-sm", "placeholder": "Підтвердіть пароль"}
        )


MOBILITY_CHOICES = [(L["id"], f"Рівень {L['id']}: {L['short']}") for L in MOBILITY_LEVELS]


class AddListingForm(forms.ModelForm):
    mobility_level = forms.ChoiceField(
        label="Рівень доступності",
        choices=[("", "— Не вказано")] + MOBILITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Property
        fields = (
            "name",
            "listing_type",
            "address",
            "city",
            "price",
            "rooms",
            "area_sqm",
            "description",
            "photo",
            "mobility_level",
            "contact_phone",
            "features",
        )
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Назва оголошення"}
            ),
            "listing_type": forms.Select(attrs={"class": "form-select"}),
            "address": forms.TextInput(attrs={"class": "form-control", "placeholder": "Адреса"}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "Місто"}),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "грн", "min": 0}
            ),
            "rooms": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "—", "min": 1, "max": 20}
            ),
            "area_sqm": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "м²", "min": 1, "step": 0.1}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Опис"}
            ),
            "photo": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "contact_phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+380 XX XXX XX XX"}
            ),
            "features": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo"].required = True

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields and hasattr(self.fields[name].widget, "attrs"):
                self.fields[name].widget.attrs.setdefault("class", "")
                if "is-invalid" not in self.fields[name].widget.attrs.get("class", ""):
                    self.fields[name].widget.attrs["class"] = (
                        self.fields[name].widget.attrs.get("class", "") + " is-invalid"
                    ).strip()

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo:
            raise forms.ValidationError(
                "Додайте хоча б одне фото оголошення. Розміщення без фото заборонено."
            )
        return photo

    def clean_mobility_level(self):
        v = self.cleaned_data.get("mobility_level")
        return int(v) if v else None

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.is_published = False
        obj.mobility_level = self.cleaned_data.get("mobility_level")
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class PaymentForm(forms.Form):
    """Форма оплати карткою (тестовий режим)."""

    card_number = forms.CharField(
        label="Номер картки",
        max_length=19,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "0000 0000 0000 0000", "maxlength": 19}
        ),
    )
    expiry_month = forms.IntegerField(
        label="Місяць",
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "MM", "min": 1, "max": 12}
        ),
    )
    expiry_year = forms.IntegerField(
        label="Рік",
        min_value=2025,
        max_value=2040,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "РРРР", "min": 2025}
        ),
    )
    cvc = forms.CharField(
        label="CVC",
        max_length=4,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "CVC", "maxlength": 4}
        ),
    )
    card_holder = forms.CharField(
        label="Ім'я на картці",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ім'я та прізвище"}),
    )

    def clean_card_number(self):
        value = self.cleaned_data.get("card_number", "")
        digits = "".join(c for c in str(value) if c.isdigit())
        if len(digits) < 13 or len(digits) > 19:
            raise forms.ValidationError("Введіть коректний номер картки (13–19 цифр).")
        return value

    def clean_expiry_month(self):
        value = self.cleaned_data.get("expiry_month")
        if value is not None and (value < 1 or value > 12):
            raise forms.ValidationError("Місяць має бути від 1 до 12.")
        return value

    def clean_expiry_year(self):
        import datetime

        value = self.cleaned_data.get("expiry_year")
        year = datetime.date.today().year
        if value is not None and value < year:
            raise forms.ValidationError("Термін дії картки вже минув.")
        if value is not None and value > 2040:
            raise forms.ValidationError("Невірний рік.")
        return value

    def clean_cvc(self):
        value = self.cleaned_data.get("cvc", "")
        digits = "".join(c for c in str(value) if c.isdigit())
        if len(digits) < 3 or len(digits) > 4:
            raise forms.ValidationError("CVC має містити 3 або 4 цифри.")
        return value

    def clean_card_holder(self):
        value = self.cleaned_data.get("card_holder", "").strip()
        if not value or len(value) < 2:
            raise forms.ValidationError("Введіть ім'я на картці.")
        return value

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields and hasattr(self.fields[name].widget, "attrs"):
                self.fields[name].widget.attrs.setdefault("class", "")
                if "is-invalid" not in self.fields[name].widget.attrs.get("class", ""):
                    self.fields[name].widget.attrs["class"] = (
                        self.fields[name].widget.attrs.get("class", "") + " is-invalid"
                    ).strip()


class AccessibilityAuditForm(forms.ModelForm):
    """Форма аудитора для введення результатів перевірки (заміри в см)."""

    entrance_access = forms.IntegerField(
        label="Доступність входу (бал 1–10)",
        min_value=1,
        max_value=10,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 10}),
    )
    lift_width_cm = forms.IntegerField(
        label="Ширина ліфта (см)",
        min_value=1,
        max_value=300,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 300}),
    )
    lift_score = forms.IntegerField(
        label="Бал ліфта (1–10)",
        min_value=1,
        max_value=10,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 10}),
    )
    thresholds_max_height_cm = forms.FloatField(
        label="Макс. висота порогів (см)",
        min_value=0,
        max_value=50,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 50, "step": 0.1}),
    )
    thresholds_score = forms.IntegerField(
        label="Бал порогів (1–10)",
        min_value=1,
        max_value=10,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 10}),
    )

    class Meta:
        model = AccessibilityAudit
        fields = [
            "entrance_access",
            "entrance_comment",
            "lift_width_cm",
            "lift_score",
            "lift_comment",
            "bathroom_type",
            "bathroom_comment",
            "thresholds_max_height_cm",
            "thresholds_score",
            "thresholds_comment",
            "turning_radius_exists",
            "turning_comment",
        ]
        widgets = {
            "entrance_comment": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "lift_comment": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "bathroom_type": forms.Select(attrs={"class": "form-select"}),
            "bathroom_comment": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "thresholds_comment": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "turning_radius_exists": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "turning_comment": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def clean_entrance_access(self):
        v = self.cleaned_data.get("entrance_access")
        if v is not None and (v < 1 or v > 10):
            raise forms.ValidationError("Бал має бути від 1 до 10.")
        return v

    def clean_lift_width_cm(self):
        v = self.cleaned_data.get("lift_width_cm")
        if v is not None and (v < 1 or v > 300):
            raise forms.ValidationError("Ширина ліфта має бути від 1 до 300 см.")
        return v

    def clean_lift_score(self):
        v = self.cleaned_data.get("lift_score")
        if v is not None and (v < 1 or v > 10):
            raise forms.ValidationError("Бал має бути від 1 до 10.")
        return v

    def clean_thresholds_max_height_cm(self):
        v = self.cleaned_data.get("thresholds_max_height_cm")
        if v is not None and (v < 0 or v > 50):
            raise forms.ValidationError("Висота порогів має бути від 0 до 50 см.")
        return v

    def clean_thresholds_score(self):
        v = self.cleaned_data.get("thresholds_score")
        if v is not None and (v < 1 or v > 10):
            raise forms.ValidationError("Бал має бути від 1 до 10.")
        return v

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Статус входу обчислюється в моделі за entrance_access
        instance.recalculate_total_score()
        if commit:
            instance.save()
        return instance


class UserProfileForm(forms.ModelForm):
    """Форма редагування профілю."""
    
    first_name = forms.CharField(label="Ім'я", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(label="Прізвище", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(label="Email", required=False, widget=forms.EmailInput(attrs={"class": "form-control"}))

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class ReviewForm(forms.ModelForm):
    """Форма для залишення відгуку."""
    
    rating = forms.ChoiceField(
        label="Оцінка",
        choices=[(i, str(i)) for i in range(5, 0, -1)],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    text = forms.CharField(
        label="Відгук",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Напишіть свій відгук..."})
    )

    class Meta:
        from .models import ProfileReview
        model = ProfileReview
        fields = ["rating", "text"]
