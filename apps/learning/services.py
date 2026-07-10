from datetime import date

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Assessment, LearningCycle


def get_member_current_cycle(member):
    """Return the active cycle containing today, otherwise the latest active cycle."""
    from django.utils import timezone

    today = timezone.localdate()
    cycle = (
        LearningCycle.objects.filter(
            status=LearningCycle.Status.ACTIVE,
            participants__member=member,
            start_date__lte=today,
            end_date__gte=today,
        )
        .order_by("-start_date")
        .first()
    )
    if cycle:
        return cycle
    return (
        LearningCycle.objects.filter(
            status=LearningCycle.Status.ACTIVE,
            participants__member=member,
        )
        .order_by("-start_date")
        .first()
    )


def _check_participant(member, cycle):
    """Return True if the member is an active participant of the cycle."""
    return cycle.participants.filter(member=member).exists() and member.is_active


def _assessment_values(assessment):
    return {
        "current_level": assessment.current_level,
        "target_level": assessment.target_level,
        "gap": assessment.gap,
        "priority": assessment.priority,
        "included": assessment.included,
        "planned_quarter": assessment.planned_quarter,
        "planned_month": (
            assessment.planned_month.isoformat() if assessment.planned_month else None
        ),
        "version": assessment.version,
    }


def _conflict_response(assessment):
    return {
        "ok": False,
        "status": 409,
        "error": "conflict",
        "version": assessment.version,
        "values": _assessment_values(assessment),
    }


def _normalize_month(value):
    if value in ("", None):
        return None
    if isinstance(value, str):
        if len(value) == 7 and value.count("-") == 1:
            value = f"{value}-01"
        value = date.fromisoformat(value)
    return value.replace(day=1)


def _coerce_int_or_none(value):
    if value in ("", None):
        return None
    return int(value)


def _parse_version(value, errors):
    if value in ("", None):
        errors["version"] = ["必须提供版本号。"]
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        errors["version"] = ["版本号必须是整数。"]
        return None


def _validate_levels(data, errors):
    for field in ("current_level", "target_level"):
        if field not in data:
            continue
        value = data[field]
        if value in ("", None):
            continue
        try:
            value = int(value)
        except (TypeError, ValueError):
            errors[field] = ["必须是整数。"]
            continue
        if value < 0 or value > 5:
            errors[field] = ["必须在 0 到 5 之间。"]


def _validate_priority(value, errors):
    if value in ("", None):
        return
    valid = [choice[0] for choice in Assessment.PRIORITY_CHOICES]
    if value not in valid:
        errors["priority"] = ["无效的优先级。"]


def _validate_quarter(value, errors):
    if value in ("", None):
        return
    valid = [choice[0] for choice in Assessment.QUARTER_CHOICES]
    if value not in valid:
        errors["planned_quarter"] = ["无效的季度。"]


def _validate_planned_month(value, errors):
    if value in ("", None):
        return
    test = value
    if isinstance(test, str):
        if len(test) == 7 and test.count("-") == 1:
            test = f"{test}-01"
        try:
            date.fromisoformat(test)
        except ValueError:
            errors["planned_month"] = ["无效的月份。"]
    elif not isinstance(value, date):
        errors["planned_month"] = ["无效的月份。"]


def _validate_included(value, errors):
    if value in ("", None):
        return
    if isinstance(value, bool):
        return
    if isinstance(value, str) and value.lower() in (
        "true", "1", "on", "yes", "false", "0", "off", "no",
    ):
        return
    errors["included"] = ["无效的布尔值。"]


def _coerce_included(value):
    if isinstance(value, bool):
        return value
    return value.lower() in ("true", "1", "on", "yes")


def save_single_assessment(assessment, data):
    """Save a single assessment row, enforcing optimistic locking and validation.

    `data` contains raw values from the client for any of:
    - current_level, target_level: int or empty
    - priority, planned_quarter: str
    - included: bool or bool-like str
    - planned_month: date, ISO string, or YYYY-MM string
    - version: int from client (required)
    """
    if not _check_participant(assessment.member, assessment.cycle):
        return {"ok": False, "status": 404, "error": "not_found"}

    if assessment.cycle.status != LearningCycle.Status.ACTIVE:
        return {"ok": False, "status": 409, "error": "archived"}

    errors = {}
    client_version = _parse_version(data.get("version"), errors)
    _validate_levels(data, errors)
    _validate_priority(data.get("priority"), errors)
    _validate_quarter(data.get("planned_quarter"), errors)
    _validate_planned_month(data.get("planned_month"), errors)
    _validate_included(data.get("included"), errors)
    if errors:
        return {"ok": False, "status": 400, "errors": errors}

    if client_version != assessment.version:
        assessment.refresh_from_db()
        return _conflict_response(assessment)

    current_level = assessment.current_level
    if "current_level" in data:
        current_level = _coerce_int_or_none(data["current_level"])
    target_level = assessment.target_level
    if "target_level" in data:
        target_level = _coerce_int_or_none(data["target_level"])
    priority = data.get("priority", assessment.priority)
    planned_quarter = data.get("planned_quarter", assessment.planned_quarter)
    planned_month = assessment.planned_month
    if "planned_month" in data:
        planned_month = _normalize_month(data["planned_month"])
    included = assessment.included
    if "included" in data:
        included = _coerce_included(data["included"])

    if current_level is not None and target_level is not None:
        gap = max(target_level - current_level, 0)
    else:
        gap = None

    updated = Assessment.objects.filter(
        pk=assessment.pk, version=assessment.version
    ).update(
        version=F("version") + 1,
        current_level=current_level,
        target_level=target_level,
        gap=gap,
        priority=priority,
        included=included,
        planned_quarter=planned_quarter,
        planned_month=planned_month,
        updated_at=timezone.now(),
    )
    if updated == 0:
        assessment.refresh_from_db()
        return _conflict_response(assessment)

    assessment.refresh_from_db()
    return {
        "ok": True,
        "version": assessment.version,
        "values": _assessment_values(assessment),
    }


def update_assessments_batch(member, assessment_ids, data):
    """Update many assessments atomically. All must belong to one active cycle."""
    errors = {}
    ids = []
    for pk in assessment_ids:
        try:
            ids.append(int(pk))
        except (TypeError, ValueError):
            errors["ids"] = ["评估 ID 必须是整数。"]
            break

    _validate_priority(data.get("priority"), errors)
    _validate_quarter(data.get("planned_quarter"), errors)
    _validate_planned_month(data.get("planned_month"), errors)
    _validate_included(data.get("included"), errors)
    if errors:
        return {"ok": False, "status": 400, "errors": errors}

    assessments = list(
        Assessment.objects.filter(pk__in=ids, member=member).select_related("cycle")
    )
    found_ids = {a.pk for a in assessments}
    if found_ids != set(ids):
        return {"ok": False, "status": 404, "error": "not_found"}

    cycles = {a.cycle for a in assessments}
    if len(cycles) != 1:
        return {"ok": False, "status": 400, "error": "mixed_cycle"}

    cycle = cycles.pop()
    if not _check_participant(member, cycle):
        return {"ok": False, "status": 404, "error": "not_found"}

    if cycle.status != LearningCycle.Status.ACTIVE:
        return {"ok": False, "status": 409, "error": "archived"}

    update_kwargs = {
        "version": F("version") + 1,
        "updated_at": timezone.now(),
    }
    if "included" in data:
        update_kwargs["included"] = _coerce_included(data["included"])
    if "priority" in data:
        update_kwargs["priority"] = data["priority"]
    if "planned_quarter" in data:
        update_kwargs["planned_quarter"] = data["planned_quarter"]
    if "planned_month" in data:
        update_kwargs["planned_month"] = _normalize_month(data["planned_month"])

    with transaction.atomic():
        Assessment.objects.filter(pk__in=ids, member=member).update(**update_kwargs)

    return {"ok": True, "updated": len(assessments), "cycle_id": cycle.pk}


def ensure_assessments_for_cycle(cycle, member):
    """Create missing assessments for active capability items."""
    cycle.create_missing_assessments(member)


def assessment_counts(cycle, member):
    """Return counts used by the assessment page."""
    qs = Assessment.objects.filter(cycle=cycle, member=member)
    total = qs.count()
    assessed = qs.exclude(
        current_level__isnull=True, target_level__isnull=True
    ).count()
    included = qs.filter(included=True).count()
    return {
        "total": total,
        "assessed": assessed,
        "included": included,
    }
