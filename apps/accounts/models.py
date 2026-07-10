from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.mail import EmailMessage, get_connection
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    pass


class EmailLogManager(models.Manager):
    def create_pending(self, recipient, trigger, subject, body):
        log = self.create(
            recipient=recipient,
            trigger=trigger,
            subject=subject,
            body=body,
            to_email=recipient.email,
        )
        if recipient.email:
            connection = get_connection(
                "django.core.mail.backends.filebased.EmailBackend",
                file_path=settings.EMAIL_FILE_PATH,
            )
            EmailMessage(subject, body, to=[recipient.email], connection=connection).send()
            log.status = EmailLog.Status.SENT
            log.sent_at = timezone.now()
            log.save(update_fields=["status", "sent_at"])
        return log


class EmailLog(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待发送"
        SENT = "sent", "已记录"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="email_logs",
    )
    trigger = models.CharField(max_length=50)
    to_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    objects = EmailLogManager()

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.trigger} -> {self.to_email or self.recipient.username}"


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
