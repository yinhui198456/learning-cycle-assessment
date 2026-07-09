from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from apps.learning.models import (
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    CapabilityMaterial,
    LearningMaterial,
)


class CapabilityCategoryTests(TestCase):
    def test_unique_name(self):
        CapabilityCategory.objects.create(name="Management", sort_order=1)
        with self.assertRaises(IntegrityError):
            CapabilityCategory.objects.create(name="Management", sort_order=2)

    def test_ordering_by_sort_order(self):
        c2 = CapabilityCategory.objects.create(name="Tech", sort_order=2)
        c1 = CapabilityCategory.objects.create(name="Management", sort_order=1)
        result = list(CapabilityCategory.objects.all())
        self.assertEqual(result, [c1, c2])

    def test_str(self):
        category = CapabilityCategory.objects.create(name="Tech", sort_order=1)
        self.assertEqual(str(category), "Tech")


class CapabilityDomainTests(TestCase):
    def setUp(self):
        self.category = CapabilityCategory.objects.create(name="Tech", sort_order=1)

    def test_unique_code(self):
        CapabilityDomain.objects.create(
            category=self.category,
            code="T01",
            name="Domain One",
            level=1,
            sort_order=1,
        )
        with self.assertRaises(IntegrityError):
            CapabilityDomain.objects.create(
                category=self.category,
                code="T01",
                name="Domain Two",
                level=1,
                sort_order=2,
            )

    def test_level_constraint(self):
        with self.assertRaises(IntegrityError):
            CapabilityDomain.objects.create(
                category=self.category,
                code="T01",
                name="Domain",
                level=3,
                sort_order=1,
            )

    def test_level1_requires_parent_null(self):
        with self.assertRaises(IntegrityError):
            CapabilityDomain.objects.create(
                category=self.category,
                code="T01",
                name="Level 1 with parent",
                level=1,
                sort_order=1,
                parent=CapabilityDomain.objects.create(
                    category=self.category,
                    code="T00",
                    name="Other",
                    level=1,
                    sort_order=0,
                ),
            )

    def test_level2_requires_parent_not_null(self):
        with self.assertRaises(IntegrityError):
            CapabilityDomain.objects.create(
                category=self.category,
                code="T02",
                name="Level 2 without parent",
                level=2,
                sort_order=1,
                parent=None,
            )

    def test_parent_self_reference(self):
        parent = CapabilityDomain.objects.create(
            category=self.category,
            code="T01",
            name="Parent",
            level=1,
            sort_order=1,
        )
        child = CapabilityDomain.objects.create(
            category=self.category,
            code="T02",
            name="Child",
            level=2,
            sort_order=1,
            parent=parent,
        )
        self.assertEqual(child.parent, parent)

    def test_category_protect(self):
        CapabilityDomain.objects.create(
            category=self.category,
            code="T01",
            name="Domain",
            level=1,
            sort_order=1,
        )
        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_parent_protect(self):
        parent = CapabilityDomain.objects.create(
            category=self.category,
            code="T01",
            name="Parent",
            level=1,
            sort_order=1,
        )
        CapabilityDomain.objects.create(
            category=self.category,
            code="T02",
            name="Child",
            level=2,
            sort_order=1,
            parent=parent,
        )
        with self.assertRaises(ProtectedError):
            parent.delete()


class LearningMaterialTests(TestCase):
    def test_unique_code(self):
        LearningMaterial.objects.create(
            code="C01-M001",
            name="Material One",
            material_type="Book",
            source="Library",
            description="Desc",
            status="Active",
        )
        with self.assertRaises(IntegrityError):
            LearningMaterial.objects.create(
                code="C01-M001",
                name="Material Two",
                material_type="Video",
                source="Web",
                description="Desc",
                status="Active",
            )

    def test_str(self):
        material = LearningMaterial.objects.create(
            code="C01-M001",
            name="Material One",
            material_type="Book",
            source="Library",
            description="Desc",
            status="Active",
        )
        self.assertEqual(str(material), "C01-M001 - Material One")


class CapabilityItemTests(TestCase):
    def setUp(self):
        self.category = CapabilityCategory.objects.create(name="Tech", sort_order=1)
        self.domain = CapabilityDomain.objects.create(
            category=self.category,
            code="T01",
            name="Domain",
            level=1,
            sort_order=1,
        )
        self.material = LearningMaterial.objects.create(
            code="C01-M001",
            name="Material",
            material_type="Book",
            source="Library",
            description="Desc",
            status="Active",
        )

    def test_unique_code(self):
        CapabilityItem.objects.create(
            domain=self.domain,
            code="I001",
            name="Item One",
            sort_order=1,
        )
        with self.assertRaises(IntegrityError):
            CapabilityItem.objects.create(
                domain=self.domain,
                code="I001",
                name="Item Two",
                sort_order=2,
            )

    def test_domain_protect(self):
        CapabilityItem.objects.create(
            domain=self.domain,
            code="I001",
            name="Item",
            sort_order=1,
        )
        with self.assertRaises(ProtectedError):
            self.domain.delete()

    def test_materials_through_model(self):
        item = CapabilityItem.objects.create(
            domain=self.domain,
            code="I001",
            name="Item",
            sort_order=1,
        )
        CapabilityMaterial.objects.create(item=item, material=self.material, sort_order=1)
        self.assertIn(self.material, item.materials.all())

    def test_material_unique_pair(self):
        item = CapabilityItem.objects.create(
            domain=self.domain,
            code="I001",
            name="Item",
            sort_order=1,
        )
        CapabilityMaterial.objects.create(item=item, material=self.material, sort_order=1)
        with self.assertRaises(IntegrityError):
            CapabilityMaterial.objects.create(item=item, material=self.material, sort_order=2)

    def test_item_cascade_deletes_link(self):
        item = CapabilityItem.objects.create(
            domain=self.domain,
            code="I001",
            name="Item",
            sort_order=1,
        )
        CapabilityMaterial.objects.create(item=item, material=self.material, sort_order=1)
        item.delete()
        self.assertFalse(CapabilityMaterial.objects.exists())

    def test_material_protect(self):
        item = CapabilityItem.objects.create(
            domain=self.domain,
            code="I001",
            name="Item",
            sort_order=1,
        )
        CapabilityMaterial.objects.create(item=item, material=self.material, sort_order=1)
        with self.assertRaises(ProtectedError):
            self.material.delete()
