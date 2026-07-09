from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from apps.learning.models import (
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    CapabilityMaterial,
    LearningMaterial,
)
from apps.learning.parser import LearningTemplateError, parse_learning_template


class Command(BaseCommand):
    help = "Import the capability catalog from the supplied Excel template."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to the Excel workbook")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist parsed data to the database (default is dry-run)",
        )

    def handle(self, *args, **options):
        path = options["path"]

        try:
            result = parse_learning_template(path)
        except LearningTemplateError as exc:
            raise CommandError(str(exc)) from exc

        if not options["apply"]:
            self.stdout.write(self.style.NOTICE("Dry run - no changes made."))
            self.stdout.write(f"  categories: {len(result['categories'])}")
            self.stdout.write(f"  domains: {len(result['domains'])}")
            self.stdout.write(f"  items: {len(result['items'])}")
            self.stdout.write(f"  materials: {len(result['materials'])}")
            return

        if self._catalog_has_data():
            raise CommandError(
                "Learning catalog already contains data. "
                "This command is a one-time initializer and will not run."
            )

        try:
            counts = self._import_data(result)
        except IntegrityError as exc:
            raise CommandError(
                "Import failed: the catalog appears to have been initialized concurrently. "
                "Please verify the database state and retry if needed."
            ) from exc
        except Exception as exc:
            raise CommandError(f"Import failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {counts['categories']} categories, "
                f"{counts['domains']} domains, "
                f"{counts['items']} items, "
                f"{counts['materials']} materials, "
                f"{counts['links']} material links."
            )
        )

    def _catalog_has_data(self):
        return (
            CapabilityCategory.objects.exists()
            or CapabilityDomain.objects.exists()
            or CapabilityItem.objects.exists()
            or LearningMaterial.objects.exists()
            or CapabilityMaterial.objects.exists()
        )

    def _import_data(self, result):
        with transaction.atomic():
            category_by_name = {}
            for category_data in result["categories"]:
                category_by_name[category_data["name"]] = CapabilityCategory.objects.create(
                    name=category_data["name"],
                    sort_order=category_data["sort_order"],
                    is_active=category_data["is_active"],
                )

            domain_by_code = {}
            for domain_data in sorted(result["domains"], key=lambda d: d["level"]):
                parent = domain_by_code.get(domain_data["parent_code"]) if domain_data["parent_code"] else None
                domain_by_code[domain_data["code"]] = CapabilityDomain.objects.create(
                    category=category_by_name[domain_data["category_name"]],
                    parent=parent,
                    code=domain_data["code"],
                    name=domain_data["name"],
                    level=domain_data["level"],
                    sort_order=domain_data["sort_order"],
                    is_active=True,
                )

            material_by_code = {}
            for material_data in result["materials"]:
                material_by_code[material_data["code"]] = LearningMaterial.objects.create(
                    code=material_data["code"],
                    name=material_data["name"],
                    material_type=material_data["material_type"],
                    source=material_data["source"],
                    description=material_data["description"],
                    status=material_data["status"],
                    is_active=True,
                )

            item_by_code = {}
            for item_data in result["items"]:
                item_by_code[item_data["code"]] = CapabilityItem.objects.create(
                    domain=domain_by_code[item_data["domain_code"]],
                    code=item_data["code"],
                    name=item_data["name"],
                    suggested_level=item_data["suggested_level"],
                    material_reference=item_data["material_reference"],
                    acceptance_method=item_data["acceptance_method"],
                    estimated_hours=item_data["estimated_hours"],
                    recommended_action=item_data["recommended_action"],
                    sort_order=item_data["sort_order"],
                    is_active=True,
                )

            links = 0
            for item_data in result["items"]:
                item = item_by_code[item_data["code"]]
                for sort_order, material_code in enumerate(item_data["material_codes"]):
                    CapabilityMaterial.objects.create(
                        item=item,
                        material=material_by_code[material_code],
                        sort_order=sort_order,
                    )
                    links += 1

            return {
                "categories": len(result["categories"]),
                "domains": len(result["domains"]),
                "items": len(result["items"]),
                "materials": len(result["materials"]),
                "links": links,
            }
