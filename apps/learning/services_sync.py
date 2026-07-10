from django.db import transaction

from .models import CatalogSyncLog, LearningCycle, PlanItem
from .services_planning import _materials_snapshot

DEFAULT_SYNC_FIELDS = ("capability_name", "suggested_level", "materials_snapshot")


def _catalog_values(capability):
    return {
        "capability_name": capability.name,
        "suggested_level": capability.suggested_level,
        "materials_snapshot": _materials_snapshot(capability),
        "task": capability.recommended_action,
        "acceptance_method": capability.acceptance_method,
        "estimated_hours": capability.estimated_hours,
    }


def _eligible_items(capability):
    return PlanItem.objects.filter(
        capability_item=capability,
        plan__cycle__status=LearningCycle.Status.ACTIVE,
    ).exclude(execution_status=PlanItem.ExecutionStatus.COMPLETED)


def preview_capability_sync(capability, fields=DEFAULT_SYNC_FIELDS):
    values = _catalog_values(capability)
    rows = []
    for item in _eligible_items(capability).select_related("plan__member", "plan__cycle"):
        changes = {}
        for field in fields:
            if field not in values:
                continue
            old = getattr(item, field)
            new = values[field]
            if old != new:
                changes[field] = (old, new)
        if changes:
            rows.append({"plan_item": item, "changes": changes})
    return rows


def sync_capability(capability, plan_item_ids, fields=DEFAULT_SYNC_FIELDS):
    values = _catalog_values(capability)
    allowed_fields = [field for field in fields if field in values]
    updated = 0
    with transaction.atomic():
        items = _eligible_items(capability).filter(pk__in=plan_item_ids)
        for item in items:
            changed_fields = []
            for field in allowed_fields:
                new = values[field]
                if getattr(item, field) != new:
                    setattr(item, field, new)
                    changed_fields.append(field)
            if changed_fields:
                item.save(update_fields=[*changed_fields, "updated_at"])
                CatalogSyncLog.objects.create(
                    capability_item=capability,
                    plan_item=item,
                    field_names=",".join(changed_fields),
                )
                updated += 1
    return updated
