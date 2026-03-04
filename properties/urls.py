from django.urls import path
from . import views

app_name = 'properties'

urlpatterns = [
    path('', views.index, name='index'),
    path('catalog/', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('faq/', views.faq, name='faq'),
    path('contact/', views.contact, name='contact'),
    path('rivni-dostupnosti/', views.accessibility_levels, name='accessibility_levels'),
    path('property/<int:pk>/', views.property_detail, name='property_detail'),
    path('property/<int:pk>/delete/', views.delete_property, name='delete_property'),
    path('audit/new/', views.auditor_form, name='auditor_form_new'),
    path('audit/<int:pk>/', views.auditor_form, name='auditor_form'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('add-listing/', views.add_listing, name='add_listing'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('payment/<int:pk>/', views.payment, name='payment'),
    path('payment/<int:pk>/paid/', views.payment_paid, name='payment_paid'),
]
