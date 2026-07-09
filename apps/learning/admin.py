from django.contrib import admin

from .models import (
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    CapabilityMaterial,
    LearningMaterial,
)


@admin.register(CapabilityCategory)
class CapabilityCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "sort_order", "is_active"]
    ordering = ["sort_order", "name"]


@admin.register(CapabilityDomain)
class CapabilityDomainAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "level", "parent", "sort_order", "is_active"]
    list_filter = ["category", "level", "is_active"]
    ordering = ["sort_order", "code"]


@admin.register(LearningMaterial)
class LearningMaterialAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "material_type", "source", "status", "is_active"]
    ordering = ["code"]


@admin.register(CapabilityItem)
class CapabilityItemAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "domain", "suggested_level", "sort_order", "is_active"]
    list_filter = ["domain__category", "domain", "is_active"]
    ordering = ["sort_order", "code"]


@admin.register(CapabilityMaterial)
class CapabilityMaterialAdmin(admin.ModelAdmin):
    list_display = ["item", "material", "sort_order"]
    ordering = ["sort_order"]
