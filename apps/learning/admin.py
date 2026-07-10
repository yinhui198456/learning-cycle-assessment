from django.contrib import admin

from .models import (
    Assessment,
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    CapabilityMaterial,
    CycleParticipant,
    LearningCycle,
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


@admin.register(CycleParticipant)
class CycleParticipantAdmin(admin.ModelAdmin):
    list_display = ["cycle", "member", "created_at"]
    list_filter = ["cycle"]


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = [
        "member",
        "cycle",
        "capability_item",
        "current_level",
        "target_level",
        "gap",
        "included",
        "version",
    ]
    list_filter = ["cycle", "included", "priority"]


@admin.register(LearningCycle)
class LearningCycleAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "cycle_type",
        "start_date",
        "end_date",
        "status",
        "created_by",
    ]
    list_filter = ["cycle_type", "status"]
    ordering = ["-start_date"]
