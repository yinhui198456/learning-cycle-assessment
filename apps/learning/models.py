from django.db import models


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
