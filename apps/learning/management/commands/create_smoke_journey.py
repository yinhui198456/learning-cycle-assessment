import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Mentorship
from apps.accounts.services import assign_buddy, has_role

User = get_user_model()


def _env_or_default(prefix, default):
    return os.environ.get(prefix, default)


class Command(BaseCommand):
    help = "Create or update dedicated smoke-test users and buddy relationship."

    def add_arguments(self, parser):
        parser.add_argument(
            "--member",
            default=_env_or_default("SMOKE_MEMBER_USER", "smoke_member"),
            help="Smoke member username (env: SMOKE_MEMBER_USER).",
        )
        parser.add_argument(
            "--buddy",
            default=_env_or_default("SMOKE_BUDDY_USER", "smoke_buddy"),
            help="Smoke buddy username (env: SMOKE_BUDDY_USER).",
        )
        parser.add_argument(
            "--leader",
            default=_env_or_default("SMOKE_LEADER_USER", "smoke_leader"),
            help="Smoke leader username (env: SMOKE_LEADER_USER).",
        )
        parser.add_argument(
            "--member-pass",
            default=_env_or_default("SMOKE_MEMBER_PASS", ""),
            help="Smoke member password (env: SMOKE_MEMBER_PASS).",
        )
        parser.add_argument(
            "--buddy-pass",
            default=_env_or_default("SMOKE_BUDDY_PASS", ""),
            help="Smoke buddy password (env: SMOKE_BUDDY_PASS).",
        )
        parser.add_argument(
            "--leader-pass",
            default=_env_or_default("SMOKE_LEADER_PASS", ""),
            help="Smoke leader password (env: SMOKE_LEADER_PASS).",
        )

    def handle(self, *args, **options):
        users_config = [
            (options["member"], options["member_pass"], "member"),
            (options["buddy"], options["buddy_pass"], "buddy"),
            (options["leader"], options["leader_pass"], "leader"),
        ]

        groups = {}
        for role in ("member", "buddy", "leader"):
            group, _ = Group.objects.get_or_create(name=role)
            groups[role] = group

        created_users = []
        with transaction.atomic():
            for username, password, role in users_config:
                if not password:
                    self.stderr.write(
                        self.style.ERROR(f"No password configured for {username}; skipping")
                    )
                    continue

                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "is_active": True,
                        "is_staff": role == "leader",
                        "is_superuser": role == "leader",
                    },
                )
                if not user.is_active:
                    user.is_active = True
                if role == "leader":
                    user.is_staff = True
                    user.is_superuser = True
                user.set_password(password)
                user.save()
                user.groups.set([groups[role]])
                if created:
                    created_users.append(username)
                self.stdout.write(
                    self.style.SUCCESS(f"{'created' if created else 'updated'} {username} as {role}")
                )

            member = User.objects.filter(username=options["member"]).first()
            buddy = User.objects.filter(username=options["buddy"]).first()

            if member and buddy:
                if not has_role(member, "member"):
                    self.stderr.write(
                        self.style.ERROR(f"{member.username} does not have member role")
                    )
                    return
                if not has_role(buddy, "buddy"):
                    self.stderr.write(
                        self.style.ERROR(f"{buddy.username} does not have buddy role")
                    )
                    return

                existing = Mentorship.objects.filter(
                    member=member, ended_at__isnull=True
                ).first()
                if existing:
                    if existing.buddy_id != buddy.pk:
                        self.stderr.write(
                            self.style.ERROR(
                                f"{member.username} already has buddy {existing.buddy.username}"
                            )
                        )
                        return
                    self.stdout.write(
                        self.style.NOTICE(
                            f"mentorship already exists: {member.username} -> {buddy.username}"
                        )
                    )
                else:
                    assign_buddy(member, buddy)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"created mentorship: {member.username} -> {buddy.username}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"smoke journey users ready: {[u for u, _, _ in users_config]}"
            )
        )
