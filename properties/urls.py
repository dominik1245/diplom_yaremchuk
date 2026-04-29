from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "properties"

urlpatterns = [
    path("", views.index, name="index"),
    path("catalog/", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("services/", views.services, name="services"),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("rivni-dostupnosti/", views.accessibility_levels, name="accessibility_levels"),
    path("property/<int:pk>/", views.property_detail, name="property_detail"),
    path("property/<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("property/<int:pk>/delete/", views.delete_property, name="delete_property"),
    path("audit/new/", views.auditor_form, name="auditor_form_new"),
    path("audit/<int:pk>/", views.auditor_form, name="auditor_form"),
    path("auth/", views.auth_page, name="auth"),
    path("auth/coming-soon/", views.coming_soon, name="coming_soon"),
    path(
        "auth/password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            success_url=reverse_lazy("properties:password_reset_done"),
            subject_template_name="registration/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "auth/password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "auth/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("properties:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "auth/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("add-listing/", views.add_listing, name="add_listing"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/<str:username>/", views.public_profile, name="public_profile"),
    path("payment/<int:pk>/", views.payment, name="payment"),
    path("payment/<int:pk>/paid/", views.payment_paid, name="payment_paid"),
    path("property/<int:pk>/promote/", views.promote_listing, name="promote_listing"),
    path("privacy-policy/", views.privacy_policy, name="privacy_policy"),
    path("terms-of-service/", views.terms_of_service, name="terms_of_service"),
]
