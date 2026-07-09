from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from apps.learning.models import (
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    CapabilityMaterial,
    LearningMaterial,
)
from apps.learning.parser import parse_learning_template


class RealWorkbookIntegrationTests(TestCase):
    def test_import_real_workbook(self):
        path = Path(settings.BASE_DIR) / "团队成员年度学习计划模板_基于能力模型_V1.3.xlsx"
        self.assertTrue(path.exists())

        call_command("import_learning_template", str(path), "--apply")

        self.assertEqual(CapabilityCategory.objects.count(), 2)
        self.assertEqual(CapabilityDomain.objects.filter(level=1).count(), 6)
        self.assertEqual(CapabilityDomain.objects.filter(level=2).count(), 47)
        self.assertEqual(CapabilityDomain.objects.count(), 53)
        self.assertEqual(CapabilityItem.objects.count(), 310)
        self.assertEqual(LearningMaterial.objects.count(), 95)

        expected_links = sum(
            len(item["material_codes"])
            for item in parse_learning_template(path)["items"]
        )
        self.assertEqual(CapabilityMaterial.objects.count(), expected_links)
