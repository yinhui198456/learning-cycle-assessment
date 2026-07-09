from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    pass


class Mentorship(models.Model):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="mentorships_as_member",
    )
    buddy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="mentorships_as_buddy",
    )
    started_at = models.DateField(default=timezone.localdate)
    ended_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["member"],
                condition=models.Q(ended_at__isnull=True),
                name="unique_active_member_mentorship",
            ),
            models.CheckConstraint(
                condition=~models.Q(member=models.F("buddy")),
                name="mentorship_member_not_buddy",
            ),
            models.CheckConstraint(
                condition=models.Q(ended_at__isnull=True)
                | models.Q(ended_at__gte=models.F("started_at")),
                name="mentorship_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.member.username} — {self.buddy.username} ({self.started_at})"
