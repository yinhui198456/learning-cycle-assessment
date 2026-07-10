from django import forms
from django.contrib.auth import get_user_model

from .models import LearningCycle, _add_months

User = get_user_model()


class LearningCycleForm(forms.Form):
    cycle_type = forms.ChoiceField(
        choices=LearningCycle.Type.choices,
        label="周期类型",
        widget=forms.Select,
    )
    year = forms.IntegerField(
        label="年份",
        required=False,
        min_value=1900,
        max_value=3000,
    )
    start_date = forms.DateField(
        label="开始日期",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True, groups__name="member").distinct(),
        label="参与成员",
        widget=forms.CheckboxSelectMultiple,
    )

    def clean(self):
        cleaned = super().clean()
        cycle_type = cleaned.get("cycle_type")
        year = cleaned.get("year")
        start_date = cleaned.get("start_date")
        members = cleaned.get("members")

        if cycle_type == LearningCycle.Type.CALENDAR_YEAR:
            if year is None:
                self.add_error("year", "自然年周期必须填写年份。")
            if start_date:
                self.add_error("start_date", "自然年周期无需填写开始日期。")

        if cycle_type == LearningCycle.Type.ROLLING_12_MONTH:
            if start_date is None:
                self.add_error("start_date", "滚动周期必须填写开始日期。")
            if year:
                self.add_error("year", "滚动周期无需填写年份。")

        if not self.errors and members:
            from datetime import date, timedelta

            if cycle_type == LearningCycle.Type.CALENDAR_YEAR:
                start = date(year, 1, 1)
                end = date(year, 12, 31)
            else:
                start = start_date
                end = _add_months(start_date, 12) - timedelta(days=1)

            overlapping = LearningCycle.objects.filter(
                status=LearningCycle.Status.ACTIVE,
                participants__member__in=members,
                start_date__lte=end,
                end_date__gte=start,
            )
            if overlapping.exists():
                self.add_error("members", "所选成员在重叠日期已有其他进行中的学习周期。")

        return cleaned

    def create_cycle(self, created_by):
        cycle_type = self.cleaned_data["cycle_type"]
        members = list(self.cleaned_data["members"])

        if cycle_type == LearningCycle.Type.CALENDAR_YEAR:
            return LearningCycle.create_calendar_year(
                year=self.cleaned_data["year"],
                members=members,
                created_by=created_by,
            )

        return LearningCycle.create_rolling_cycle(
            start_date=self.cleaned_data["start_date"],
            members=members,
            created_by=created_by,
        )
