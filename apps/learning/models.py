import calendar
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class CapabilityCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "capability category"
        verbose_name_plural = "capability categories"

    def __str__(self):
        return self.name


class CapabilityDomain(models.Model):
    LEVEL_CHOICES = [
        (1, "Level 1"),
        (2, "Level 2"),
    ]

    category = models.ForeignKey(
        CapabilityCategory,
        on_delete=models.PROTECT,
        related_name="domains",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    level = models.PositiveSmallIntegerField(choices=LEVEL_CHOICES)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "code"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(level__in=[1, 2]),
                name="learning_domain_level_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(level=1, parent__isnull=True)
                    | models.Q(level=2, parent__isnull=False)
                ),
                name="learning_domain_level_parent_consistent",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class LearningMaterial(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    material_type = models.CharField(max_length=100, blank=True)
    source = models.TextField(blank=True)
    description = models.TextField(blank=True)
    status = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class CapabilityItem(models.Model):
    domain = models.ForeignKey(
        CapabilityDomain,
        on_delete=models.PROTECT,
        related_name="items",
    )
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    suggested_level = models.CharField(max_length=50, blank=True)
    material_reference = models.TextField(blank=True)
    acceptance_method = models.TextField(blank=True)
    estimated_hours = models.CharField(max_length=50, blank=True)
    recommended_action = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    materials = models.ManyToManyField(
        LearningMaterial,
        through="CapabilityMaterial",
        related_name="capability_items",
    )

    class Meta:
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class CapabilityMaterial(models.Model):
    item = models.ForeignKey(
        CapabilityItem,
        on_delete=models.CASCADE,
        related_name="capability_materials",
    )
    material = models.ForeignKey(
        LearningMaterial,
        on_delete=models.PROTECT,
        related_name="capability_materials",
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["item", "material"],
                name="learning_item_material_unique",
            ),
        ]

    def __str__(self):
        return f"{self.item.code} <-> {self.material.code}"


def _add_months(source: date, months: int) -> date:
    """Return a date shifted forward by the given number of months."""
    month = source.month - 1 + months
    year = source.year + month // 12
    month = month % 12 + 1
    day = min(source.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class LearningCycle(models.Model):
    class Type(models.TextChoices):
        CALENDAR_YEAR = "calendar_year", "自然年"
        ROLLING_12_MONTH = "rolling_12_month", "连续 12 个月"

    class Status(models.TextChoices):
        ACTIVE = "active", "进行中"
        ARCHIVED = "archived", "已归档"

    name = models.CharField(max_length=200, unique=True)
    cycle_type = models.CharField(max_length=20, choices=Type.choices)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_cycles",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="learning_cycle_end_after_start",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        cycle_type="calendar_year",
                        year__isnull=False,
                    )
                    | models.Q(
                        cycle_type="rolling_12_month",
                        year__isnull=True,
                    )
                ),
                name="learning_cycle_year_consistent",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.cycle_type == self.Type.CALENDAR_YEAR and self.year:
            self.start_date = date(self.year, 1, 1)
            self.end_date = date(self.year, 12, 31)
            self.name = f"{self.year} 年度学习周期"
        elif self.cycle_type == self.Type.ROLLING_12_MONTH and self.start_date:
            if self.end_date is None:
                self.end_date = _add_months(self.start_date, 12) - timedelta(days=1)
            self.name = f"{self.start_date} 至 {self.end_date} 学习周期"

        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("结束日期不能早于开始日期。")

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.cycle_type == self.Type.CALENDAR_YEAR and not self.year:
            raise ValidationError({"year": "自然年周期必须填写年份。"})

    @classmethod
    def create_calendar_year(cls, year, members, created_by):
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        name = f"{year} 年度学习周期"
        with transaction.atomic():
            cycle = cls.objects.create(
                cycle_type=cls.Type.CALENDAR_YEAR,
                year=year,
                start_date=start_date,
                end_date=end_date,
                name=name,
                created_by=created_by,
            )
            for member in members:
                cycle.add_participant(member)
        return cycle

    @classmethod
    def create_rolling_cycle(cls, start_date, members, created_by):
        end_date = _add_months(start_date, 12) - timedelta(days=1)
        name = f"{start_date} 至 {end_date} 学习周期"
        with transaction.atomic():
            cycle = cls.objects.create(
                cycle_type=cls.Type.ROLLING_12_MONTH,
                start_date=start_date,
                end_date=end_date,
                name=name,
                created_by=created_by,
            )
            for member in members:
                cycle.add_participant(member)
        return cycle

    def add_participant(self, member):
        if not member.is_active or not member.groups.filter(name="member").exists():
            raise ValueError("参与者必须是启用的成员。")

        from apps.accounts.services import has_role

        if not has_role(member, "member"):
            raise ValueError("参与者必须具有 member 角色。")

        overlap = LearningCycle.objects.filter(
            status=self.Status.ACTIVE,
            participants__member=member,
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
        ).exclude(pk=self.pk)
        if overlap.exists():
            raise ValueError("该成员在重叠日期已有其他进行中的学习周期。")

        participant, _ = CycleParticipant.objects.get_or_create(
            cycle=self, member=member
        )
        self.create_missing_assessments(member)
        return participant

    def create_missing_assessments(self, member=None):
        if member is not None:
            members = [member.pk]
        else:
            members = list(
                self.participants.values_list("member_id", flat=True)
            )
        existing_items = set(
            Assessment.objects.filter(cycle=self, member_id__in=members).values_list(
                "member_id", "capability_item_id"
            )
        )
        active_items = list(CapabilityItem.objects.filter(is_active=True))
        to_create = []
        for user_id in members:
            for item in active_items:
                if (user_id, item.pk) not in existing_items:
                    to_create.append(
                        Assessment(cycle=self, member_id=user_id, capability_item=item)
                    )
        Assessment.objects.bulk_create(to_create)


class CycleParticipant(models.Model):
    cycle = models.ForeignKey(
        LearningCycle,
        on_delete=models.PROTECT,
        related_name="participants",
    )
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cycle_participations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cycle", "member"],
                name="learning_cycle_participant_unique",
            ),
        ]

    def __str__(self):
        return f"{self.member.username} in {self.cycle.name}"


class Assessment(models.Model):
    PRIORITY_CHOICES = [
        ("", "未设置"),
        ("high", "高"),
        ("medium", "中"),
        ("low", "低"),
    ]
    QUARTER_CHOICES = [
        ("", "未设置"),
        ("Q1", "Q1"),
        ("Q2", "Q2"),
        ("Q3", "Q3"),
        ("Q4", "Q4"),
    ]

    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessments",
    )
    cycle = models.ForeignKey(
        LearningCycle,
        on_delete=models.PROTECT,
        related_name="assessments",
    )
    capability_item = models.ForeignKey(
        CapabilityItem,
        on_delete=models.PROTECT,
        related_name="assessments",
    )
    current_level = models.PositiveSmallIntegerField(null=True, blank=True)
    target_level = models.PositiveSmallIntegerField(null=True, blank=True)
    gap = models.PositiveSmallIntegerField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, blank=True)
    included = models.BooleanField(default=False)
    planned_quarter = models.CharField(
        max_length=3, choices=QUARTER_CHOICES, blank=True
    )
    planned_month = models.DateField(null=True, blank=True)
    version = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["member", "cycle", "capability_item"],
                name="learning_assessment_unique",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(current_level__isnull=True)
                    | models.Q(current_level__gte=0, current_level__lte=5)
                ),
                name="learning_assessment_current_level_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(target_level__isnull=True)
                    | models.Q(target_level__gte=0, target_level__lte=5)
                ),
                name="learning_assessment_target_level_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(gap__isnull=True) | models.Q(gap__gte=0)
                ),
                name="learning_assessment_gap_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.member.username} — {self.capability_item.code}"

    def save(self, *args, **kwargs):
        if self.current_level is not None and self.target_level is not None:
            self.gap = max(self.target_level - self.current_level, 0)
        else:
            self.gap = None
        if self.planned_month:
            self.planned_month = self.planned_month.replace(day=1)
        super().save(*args, **kwargs)


class LearningPlan(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PENDING_APPROVAL = "pending_approval", "待 Buddy 审批"
        CHANGES_REQUESTED = "changes_requested", "需修改"
        ACTIVE = "active", "执行中"

    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="learning_plans",
    )
    cycle = models.ForeignKey(
        LearningCycle,
        on_delete=models.PROTECT,
        related_name="learning_plans",
    )
    buddy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="buddy_learning_plans",
    )
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.DRAFT
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "cycle"],
                name="learning_plan_member_cycle_unique",
            ),
        ]

    def __str__(self):
        return f"{self.member.username} — {self.cycle.name}"


class PlanItem(models.Model):
    plan = models.ForeignKey(
        LearningPlan,
        on_delete=models.CASCADE,
        related_name="items",
    )
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.PROTECT,
        related_name="plan_items",
    )
    capability_item = models.ForeignKey(
        CapabilityItem,
        on_delete=models.PROTECT,
        related_name="plan_items",
    )
    capability_code = models.CharField(max_length=20)
    capability_name = models.CharField(max_length=200)
    suggested_level = models.CharField(max_length=50, blank=True)
    materials_snapshot = models.TextField(blank=True)
    current_level = models.PositiveSmallIntegerField(null=True, blank=True)
    target_level = models.PositiveSmallIntegerField(null=True, blank=True)
    gap = models.PositiveSmallIntegerField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=Assessment.PRIORITY_CHOICES, blank=True)
    planned_quarter = models.CharField(
        max_length=3, choices=Assessment.QUARTER_CHOICES, blank=True
    )
    planned_month = models.DateField(null=True, blank=True)
    task = models.TextField(blank=True)
    acceptance_method = models.TextField(blank=True)
    estimated_hours = models.CharField(max_length=50, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "capability_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "assessment"],
                name="learning_plan_item_assessment_unique",
            ),
        ]

    def __str__(self):
        return f"{self.plan} — {self.capability_code}"

    def save(self, *args, **kwargs):
        if self.planned_month:
            self.planned_month = self.planned_month.replace(day=1)
        super().save(*args, **kwargs)


class PlanApprovalEvent(models.Model):
    class Action(models.TextChoices):
        SUBMITTED = "submitted", "已提交"
        CHANGES_REQUESTED = "changes_requested", "退回修改"
        APPROVED = "approved", "已批准"

    plan = models.ForeignKey(
        LearningPlan,
        on_delete=models.CASCADE,
        related_name="approval_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="plan_approval_events",
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"{self.plan} — {self.action}"
