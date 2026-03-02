from django.contrib import admin
from .models import Property, AccessibilityAudit, Feature


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'listing_type', 'city', 'price', 'rooms', 'area_sqm', 'mobility_level', 'is_published', 'created_at')
    list_filter = ('listing_type', 'is_published', 'city', 'mobility_level')
    search_fields = ('name', 'address', 'city', 'description')
    list_editable = ('is_published',)
    filter_horizontal = ('features',)


@admin.register(AccessibilityAudit)
class AccessibilityAuditAdmin(admin.ModelAdmin):
    list_display = ('property', 'entrance_access', 'lift_width_cm', 'bathroom_type', 'total_score', 'updated_at')
    list_filter = ('bathroom_type', 'turning_radius_exists')
    raw_id_fields = ('property',)
