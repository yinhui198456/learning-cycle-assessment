import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


@pytest.mark.django_db
def test_email_log_records_pending_message_and_file_backend(settings, tmp_path):
    from apps.accounts.models import EmailLog

    settings.EMAIL_FILE_PATH = tmp_path
    user = User.objects.create_user(
        username="member", password="testpass123", email="member@example.com"
    )
    user.groups.add(Group.objects.get(name="member"))

    log = EmailLog.objects.create_pending(
        recipient=user,
        trigger="plan_submitted",
        subject="学习计划待审批",
        body="请处理年度学习计划。",
    )

    assert log.recipient == user
    assert log.status == EmailLog.Status.SENT
    assert log.sent_at is not None
    assert "member@example.com" in log.to_email
    assert any(tmp_path.iterdir())
