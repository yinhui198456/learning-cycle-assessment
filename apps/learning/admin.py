from django.contrib import admin

from .models import (
    Assessment,
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    CapabilityMaterial,
    CycleParticipant,
    EvidenceAttachment,
    EvidenceSubmission,
    GuidanceComment,
    LearningCycle,
    LearningMaterial,
    LearningPlan,
    PlanApprovalEvent,
    PlanItem,
    ProgressUpdate,
    ReviewDecision,
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


@admin.register(LearningPlan)
class LearningPlanAdmin(admin.ModelAdmin):
    list_display = ["member", "cycle", "buddy", "status", "submitted_at", "approved_at"]
    list_filter = ["status", "cycle"]
    ordering = ["-updated_at"]


@admin.register(PlanItem)
class PlanItemAdmin(admin.ModelAdmin):
    list_display = [
        "plan",
        "capability_code",
        "capability_name",
        "priority",
        "planned_month",
        "execution_status",
    ]
    list_filter = ["plan__cycle", "priority", "execution_status"]
    ordering = ["plan", "sort_order", "capability_code"]


@admin.register(PlanApprovalEvent)
class PlanApprovalEventAdmin(admin.ModelAdmin):
    list_display = ["plan", "actor", "action", "created_at"]
    list_filter = ["action"]
    ordering = ["-created_at"]


@admin.register(ProgressUpdate)
class ProgressUpdateAdmin(admin.ModelAdmin):
    list_display = ["plan_item", "author", "hours_spent", "created_at"]
    ordering = ["-created_at"]


@admin.register(GuidanceComment)
class GuidanceCommentAdmin(admin.ModelAdmin):
    list_display = ["plan_item", "author", "created_at"]
    ordering = ["-created_at"]


@admin.register(EvidenceSubmission)
class EvidenceSubmissionAdmin(admin.ModelAdmin):
    list_display = ["plan_item", "submitted_by", "batch_no", "created_at"]
    ordering = ["-created_at"]


@admin.register(EvidenceAttachment)
class EvidenceAttachmentAdmin(admin.ModelAdmin):
    list_display = ["submission", "original_name", "content_type", "size_bytes"]


@admin.register(ReviewDecision)
class ReviewDecisionAdmin(admin.ModelAdmin):
    list_display = ["submission", "reviewer", "decision", "created_at"]
    list_filter = ["decision"]
    ordering = ["-created_at"]
