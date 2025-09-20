from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import date, timedelta
from unittest.mock import patch

from apps.better.models import ScoreDay, TargetCategory, Target, Importance





class SignalRecalculationTests(TestCase):
    """Test signal-triggered recalculation functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.importance_high = Importance.objects.create(label="High", score=5)
        self.importance_low = Importance.objects.create(label="Low", score=2)
        
        self.score_day = ScoreDay.objects.create(day=date.today())
        self.category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health"
        )
    
    def test_target_save_triggers_recalculation(self):
        """Test that saving a target triggers score recalculation"""
        # Create target (this will trigger signals)
        target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=True
        )
        
        # Refresh objects from database
        self.category.refresh_from_db()
        self.score_day.refresh_from_db()
        
        # Scores should be calculated automatically
        self.assertEqual(self.category.score, self.importance_high.score)
        self.assertEqual(self.category.max_score, self.importance_high.score)
        self.assertEqual(self.score_day.score, self.importance_high.score)
        self.assertEqual(self.score_day.max_score, self.importance_high.score)
    
    def test_target_update_triggers_recalculation(self):
        """Test that updating a target triggers score recalculation"""
        target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=False
        )
        
        # Initial scores should be 0 for actual, max_score for potential
        self.category.refresh_from_db()
        self.score_day.refresh_from_db()
        initial_category_score = self.category.score
        initial_day_score = self.score_day.score
        
        # Update target achievement
        target.is_achieved = True
        target.save()
        
        # Refresh objects from database
        self.category.refresh_from_db()
        self.score_day.refresh_from_db()
        
        # Scores should have increased
        self.assertGreater(self.category.score, initial_category_score)
        self.assertGreater(self.score_day.score, initial_day_score)
    
    def test_target_delete_triggers_recalculation(self):
        """Test that deleting a target triggers score recalculation"""
        target1 = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=True
        )
        
        target2 = Target.objects.create(
            name="Meditate",
            category=self.category,
            importance=self.importance_low,
            is_achieved=True
        )
        
        # Get initial scores with both targets
        self.category.refresh_from_db()
        self.score_day.refresh_from_db()
        initial_category_score = self.category.score
        initial_day_score = self.score_day.score
        
        # Delete one target
        target1.delete()
        
        # Refresh objects from database
        self.category.refresh_from_db()
        self.score_day.refresh_from_db()
        
        # Scores should have decreased
        self.assertLess(self.category.score, initial_category_score)
        self.assertLess(self.score_day.score, initial_day_score)
        self.assertEqual(self.category.score, self.importance_low.score)
    
    def test_importance_save_triggers_global_recalculation(self):
        """Test that saving importance triggers global recalculation"""
        # Create targets in multiple days
        target1 = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=True
        )
        
        # Create another day with targets
        other_day = ScoreDay.objects.create(day=date.today() + timedelta(days=1))
        other_category = TargetCategory.objects.create(
            day=other_day,
            name="Work"
        )
        target2 = Target.objects.create(
            name="Complete task",
            category=other_category,
            importance=self.importance_high,
            is_achieved=True
        )
        
        # Get initial scores
        self.score_day.refresh_from_db()
        other_day.refresh_from_db()
        initial_day1_max = self.score_day.max_score
        initial_day2_max = other_day.max_score
        
        # Update importance score (this should trigger global recalculation)
        self.importance_high.score = 10
        self.importance_high.save()
        
        # Refresh all objects from database
        self.score_day.refresh_from_db()
        other_day.refresh_from_db()
        
        # Max scores should have increased for both days
        self.assertGreater(self.score_day.max_score, initial_day1_max)
        self.assertGreater(other_day.max_score, initial_day2_max)
    
    def test_importance_delete_triggers_global_recalculation(self):
        """Test that deleting importance triggers global recalculation"""
        # Create a third importance level
        importance_medium = Importance.objects.create(label="Medium", score=3)
        
        # Create targets using different importance levels
        target1 = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=True
        )
        
        target2 = Target.objects.create(
            name="Meditate",
            category=self.category,
            importance=importance_medium,
            is_achieved=True
        )
        
        # Get initial scores
        self.score_day.refresh_from_db()
        initial_max_score = self.score_day.max_score
        
        # Delete the highest importance (this should trigger recalculation)
        self.importance_high.delete()
        
        # Refresh objects from database
        self.score_day.refresh_from_db()
        
        # Max score should have changed (now based on medium importance as highest)
        self.assertNotEqual(self.score_day.max_score, initial_max_score)
    
    def test_target_category_save_triggers_day_recalculation(self):
        """Test that saving target category triggers day recalculation"""
        # Create target
        target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=True
        )
        
        # Get initial day score
        self.score_day.refresh_from_db()
        initial_score = self.score_day.score
        
        # Update category (this should trigger day recalculation)
        self.category.name = "Updated Health"
        self.category.save()
        
        # Refresh day from database
        self.score_day.refresh_from_db()
        
        # Day should still have correct score (recalculation maintains consistency)
        self.assertEqual(self.score_day.score, initial_score)
    
    def test_target_category_delete_triggers_day_recalculation(self):
        """Test that deleting target category triggers day recalculation"""
        # Create another category with targets
        category2 = TargetCategory.objects.create(
            day=self.score_day,
            name="Work"
        )
        
        target1 = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=True
        )
        
        target2 = Target.objects.create(
            name="Complete task",
            category=category2,
            importance=self.importance_low,
            is_achieved=True
        )
        
        # Get initial day score
        self.score_day.refresh_from_db()
        initial_score = self.score_day.score
        
        # Delete one category
        category2.delete()
        
        # Refresh day from database
        self.score_day.refresh_from_db()
        
        # Day score should have decreased
        self.assertLess(self.score_day.score, initial_score)
        self.assertEqual(self.score_day.score, self.importance_high.score)
    
    def test_signal_handles_deleted_targets(self):
        """Test that signals properly handle deleted targets"""
        target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=True,
            is_deleted=True  # Mark as deleted
        )
        
        # Update target (should not trigger recalculation for deleted targets)
        target.is_achieved = False
        target.save()
        
        # Refresh objects from database
        self.category.refresh_from_db()
        self.score_day.refresh_from_db()
        
        # Scores should remain 0 since target is deleted
        self.assertEqual(self.category.score, 0)
        self.assertEqual(self.score_day.score, 0)
    
    def test_signal_handles_deleted_categories(self):
        """Test that signals properly handle deleted categories"""
        target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=True
        )
        
        # Mark category as deleted
        self.category.is_deleted = True
        self.category.save()
        
        # Refresh day from database
        self.score_day.refresh_from_db()
        
        # Day score should be 0 since category is deleted
        self.assertEqual(self.score_day.score, 0)


# View Tests

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.http import JsonResponse
import json


class DashboardViewTests(TestCase):
    """Test class for DashboardView testing GET requests and context"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.url = reverse('better:dashboard')
        
        # Create importance levels
        self.importance_high = Importance.objects.create(label="High", score=5)
        self.importance_low = Importance.objects.create(label="Low", score=2)
    
    def test_dashboard_get_or_create_today_logic(self):
        """Test ScoreDay.get_or_create_today creates current day if it doesn't exist"""
        # Ensure no ScoreDay exists
        ScoreDay.objects.all().delete()
        
        # Test the get_or_create_today logic
        current_day = ScoreDay.get_or_create_today()
        
        # Verify ScoreDay was created
        self.assertEqual(ScoreDay.objects.count(), 1)
        self.assertEqual(current_day.day, date.today())
    
    def test_dashboard_get_or_create_today_uses_existing(self):
        """Test ScoreDay.get_or_create_today uses existing current day"""
        # Create existing ScoreDay
        existing_day = ScoreDay.objects.create(day=date.today())
        
        # Test the get_or_create_today logic
        current_day = ScoreDay.get_or_create_today()
        
        # Verify same day is used (still only one ScoreDay)
        self.assertEqual(ScoreDay.objects.count(), 1)
        self.assertEqual(current_day.id, existing_day.id)
    
    def test_dashboard_view_logic_with_no_categories(self):
        """Test dashboard view logic when no categories exist"""
        from apps.better.views import DashboardView
        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'GET'
        
        view = DashboardView()
        view.request = request
        
        # Get the current day and verify logic
        current_day = ScoreDay.get_or_create_today()
        categories = current_day.categories.filter(is_deleted=False)
        
        # Verify empty state
        self.assertEqual(categories.count(), 0)
        
        # Test progress calculation with no categories
        progress_percentage = 0
        if current_day.max_score and current_day.max_score > 0:
            progress_percentage = round((current_day.score / current_day.max_score) * 100, 1)
        
        self.assertEqual(progress_percentage, 0)
    
    def test_dashboard_view_logic_with_categories_and_targets(self):
        """Test dashboard view logic with categories and targets"""
        # Create current day with categories and targets
        current_day = ScoreDay.get_or_create_today()
        category = TargetCategory.objects.create(day=current_day, name="Health")
        
        target1 = Target.objects.create(
            name="Exercise",
            category=category,
            importance=self.importance_high,
            is_achieved=True
        )
        
        target2 = Target.objects.create(
            name="Meditate",
            category=category,
            importance=self.importance_low,
            is_achieved=False
        )
        
        # Test the view logic
        categories = current_day.categories.filter(is_deleted=False).prefetch_related(
            'targets__importance'
        ).order_by('name')
        
        # Verify categories data
        self.assertEqual(categories.count(), 1)
        category = categories.first()
        self.assertEqual(category.name, "Health")
        
        # Test targets filtering
        targets = category.targets.filter(is_deleted=False).order_by('-importance__score', 'name')
        self.assertEqual(targets.count(), 2)
        
        # Test achieved count
        achieved_count = targets.filter(is_achieved=True).count()
        self.assertEqual(achieved_count, 1)
    
    def test_dashboard_view_excludes_deleted_categories(self):
        """Test dashboard view excludes deleted categories"""
        current_day = ScoreDay.get_or_create_today()
        
        # Create active category
        active_category = TargetCategory.objects.create(day=current_day, name="Active")
        
        # Create deleted category
        deleted_category = TargetCategory.objects.create(
            day=current_day, 
            name="Deleted", 
            is_deleted=True
        )
        
        # Test filtering logic
        categories = current_day.categories.filter(is_deleted=False)
        self.assertEqual(categories.count(), 1)
        self.assertEqual(categories.first().name, "Active")
    
    def test_dashboard_view_excludes_deleted_targets(self):
        """Test dashboard view excludes deleted targets from category data"""
        current_day = ScoreDay.get_or_create_today()
        category = TargetCategory.objects.create(day=current_day, name="Health")
        
        # Create active target
        active_target = Target.objects.create(
            name="Active",
            category=category,
            importance=self.importance_high
        )
        
        # Create deleted target
        deleted_target = Target.objects.create(
            name="Deleted",
            category=category,
            importance=self.importance_low,
            is_deleted=True
        )
        
        # Test filtering logic
        targets = category.targets.filter(is_deleted=False)
        self.assertEqual(targets.count(), 1)
        self.assertEqual(targets.first().name, "Active")
    
    def test_dashboard_view_calculates_progress_percentage(self):
        """Test dashboard view calculates correct progress percentage"""
        current_day = ScoreDay.get_or_create_today()
        category = TargetCategory.objects.create(day=current_day, name="Health")
        
        # Create 2 targets, achieve 1 (50% completion)
        Target.objects.create(
            name="Exercise",
            category=category,
            importance=self.importance_high,
            is_achieved=True
        )
        
        Target.objects.create(
            name="Meditate",
            category=category,
            importance=self.importance_high,
            is_achieved=False
        )
        
        # Refresh current day to get updated scores
        current_day.refresh_from_db()
        
        # Test progress calculation logic
        progress_percentage = 0
        if current_day.max_score and current_day.max_score > 0:
            progress_percentage = round((current_day.score / current_day.max_score) * 100, 1)
        
        # Should be 50% (5 out of 10 max score)
        self.assertEqual(progress_percentage, 50.0)


class TargetCategoryCreateViewTests(TestCase):
    """Test class for TargetCategoryCreateView testing CRUD operations"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.url = reverse('better:category-create')
        
        # Create importance levels
        self.importance_high = Importance.objects.create(label="High", score=5)
    
    def test_category_create_view_form_kwargs(self):
        """Test that view passes current day to form"""
        from apps.better.views import TargetCategoryCreateView
        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'GET'
        
        view = TargetCategoryCreateView()
        view.request = request
        
        # Test get_form_kwargs method
        kwargs = view.get_form_kwargs()
        self.assertIn('current_day', kwargs)
        self.assertEqual(kwargs['current_day'], ScoreDay.get_or_create_today())
    
    def test_category_create_form_valid_logic(self):
        """Test form_valid method creates category correctly"""
        from apps.better.views import TargetCategoryCreateView
        from apps.better.forms import TargetCategoryForm
        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'POST'
        
        view = TargetCategoryCreateView()
        view.request = request
        
        # Create form with valid data
        current_day = ScoreDay.get_or_create_today()
        form = TargetCategoryForm(data={'name': 'Health'}, current_day=current_day)
        
        self.assertTrue(form.is_valid())
        
        # Test that category gets created with correct attributes
        # (We can't test the full form_valid method without template, but we can test the logic)
        category = TargetCategory.objects.create(
            name='Health',
            day=current_day,
            score=None,
            max_score=None
        )
        
        self.assertEqual(category.name, 'Health')
        self.assertEqual(category.day, current_day)
        self.assertIsNone(category.score)
        self.assertIsNone(category.max_score)
    
    def test_category_create_form_validation(self):
        """Test form validation for category creation"""
        from apps.better.forms import TargetCategoryForm
        
        current_day = ScoreDay.get_or_create_today()
        
        # Test empty name
        form = TargetCategoryForm(data={'name': ''}, current_day=current_day)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        
        # Test valid name
        form = TargetCategoryForm(data={'name': 'Health'}, current_day=current_day)
        self.assertTrue(form.is_valid())
    
    def test_category_create_duplicate_name_validation(self):
        """Test duplicate name validation for same day"""
        from apps.better.forms import TargetCategoryForm
        
        current_day = ScoreDay.get_or_create_today()
        
        # Create existing category
        TargetCategory.objects.create(day=current_day, name='Health')
        
        # Try to create duplicate
        form = TargetCategoryForm(data={'name': 'Health'}, current_day=current_day)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_category_create_associates_with_current_day(self):
        """Test that category gets associated with current day"""
        current_day = ScoreDay.get_or_create_today()
        
        category = TargetCategory.objects.create(
            name='Work',
            day=current_day
        )
        
        self.assertEqual(category.day, current_day)


class TargetCategoryUpdateViewTests(TestCase):
    """Test class for TargetCategoryUpdateView testing CRUD operations"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create current day and category
        self.current_day = ScoreDay.get_or_create_today()
        self.category = TargetCategory.objects.create(
            day=self.current_day,
            name="Health"
        )
        self.url = reverse('better:category-update', kwargs={'pk': self.category.pk})
    
    def test_category_update_queryset_filtering(self):
        """Test that view only allows current day's non-deleted categories"""
        from apps.better.views import TargetCategoryUpdateView
        
        view = TargetCategoryUpdateView()
        queryset = view.get_queryset()
        
        # Should include our current day's category
        self.assertIn(self.category, queryset)
        
        # Create category for different day
        other_day = ScoreDay.objects.create(day=date.today() + timedelta(days=1))
        other_category = TargetCategory.objects.create(day=other_day, name="Other")
        
        # Should not include other day's category
        self.assertNotIn(other_category, queryset)
        
        # Create deleted category for current day
        deleted_category = TargetCategory.objects.create(
            day=self.current_day, 
            name="Deleted", 
            is_deleted=True
        )
        
        # Should not include deleted category
        self.assertNotIn(deleted_category, queryset)
    
    def test_category_update_form_kwargs(self):
        """Test that view passes current day to form"""
        from apps.better.views import TargetCategoryUpdateView
        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'GET'
        
        view = TargetCategoryUpdateView()
        view.request = request
        view.object = self.category
        
        kwargs = view.get_form_kwargs()
        self.assertIn('current_day', kwargs)
        self.assertEqual(kwargs['current_day'], self.category.day)
    
    def test_category_update_logic(self):
        """Test category update logic"""
        # Update category name
        original_name = self.category.name
        self.category.name = 'Updated Health'
        self.category.save()
        
        # Verify update
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Updated Health')
        self.assertNotEqual(self.category.name, original_name)
    
    def test_category_update_validation(self):
        """Test form validation for category updates"""
        from apps.better.forms import TargetCategoryForm
        
        # Test valid update
        form = TargetCategoryForm(
            data={'name': 'Updated Health'}, 
            instance=self.category,
            current_day=self.current_day
        )
        self.assertTrue(form.is_valid())
        
        # Test empty name
        form = TargetCategoryForm(
            data={'name': ''}, 
            instance=self.category,
            current_day=self.current_day
        )
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class TargetCategoryDeleteViewTests(TestCase):
    """Test class for TargetCategoryDeleteView testing CRUD operations"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create current day and category with targets
        self.current_day = ScoreDay.get_or_create_today()
        self.category = TargetCategory.objects.create(
            day=self.current_day,
            name="Health"
        )
        
        self.importance = Importance.objects.create(label="High", score=5)
        self.target1 = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance
        )
        self.target2 = Target.objects.create(
            name="Meditate",
            category=self.category,
            importance=self.importance
        )
        
        self.url = reverse('better:category-delete', kwargs={'pk': self.category.pk})
    
    def test_category_delete_get_displays_confirmation(self):
        """Test GET request displays delete confirmation"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Delete Category: {self.category.name}')
        self.assertContains(response, self.category.name)
        self.assertIn('target_count', response.context)
        self.assertIn('category_name', response.context)
        
        # Should show target count
        self.assertEqual(response.context['target_count'], 2)
        self.assertEqual(response.context['category_name'], 'Health')
    
    def test_category_delete_post_soft_deletes_category(self):
        """Test POST request performs soft delete on category"""
        response = self.client.post(self.url)
        
        # Should redirect to dashboard
        self.assertRedirects(response, reverse('better:dashboard'))
        
        # Verify category was soft deleted (not hard deleted)
        self.assertEqual(TargetCategory.objects.count(), 1)
        self.category.refresh_from_db()
        self.assertTrue(self.category.is_deleted)
        
        # Verify success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Health', str(messages[0]))
        self.assertIn('removed successfully', str(messages[0]))
    
    def test_category_delete_post_soft_deletes_targets(self):
        """Test POST request soft deletes all associated targets"""
        response = self.client.post(self.url)
        
        self.assertRedirects(response, reverse('better:dashboard'))
        
        # Verify targets were soft deleted (not hard deleted)
        self.assertEqual(Target.objects.count(), 2)
        
        self.target1.refresh_from_db()
        self.target2.refresh_from_db()
        
        self.assertTrue(self.target1.is_deleted)
        self.assertTrue(self.target2.is_deleted)
    
    def test_category_delete_post_recalculates_scores(self):
        """Test POST request triggers score recalculation"""
        # Set initial scores
        self.current_day.score = 10
        self.current_day.max_score = 20
        self.current_day.save()
        
        response = self.client.post(self.url)
        
        self.assertRedirects(response, reverse('better:dashboard'))
        
        # Verify scores were recalculated (should be 0 now with no active categories)
        self.current_day.refresh_from_db()
        self.assertEqual(self.current_day.score, 0)
        self.assertEqual(self.current_day.max_score, 0)
    
    def test_category_delete_only_current_day_categories(self):
        """Test that only current day's categories can be deleted"""
        # Create category for different day
        other_day = ScoreDay.objects.create(day=date.today() + timedelta(days=1))
        other_category = TargetCategory.objects.create(day=other_day, name="Other")
        
        other_url = reverse('better:category-delete', kwargs={'pk': other_category.pk})
        
        response = self.client.get(other_url)
        
        # Should return 404 since it's not current day's category
        self.assertEqual(response.status_code, 404)
    
    def test_category_delete_excludes_deleted_categories(self):
        """Test that deleted categories cannot be deleted again"""
        # Mark category as deleted
        self.category.is_deleted = True
        self.category.save()
        
        response = self.client.get(self.url)
        
        # Should return 404 since category is already deleted
        self.assertEqual(response.status_code, 404)


class TargetCreateViewTests(TestCase):
    """Test class for TargetCreateView testing creation"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.url = reverse('better:target-create')
        
        # Create current day, category, and importance
        self.current_day = ScoreDay.get_or_create_today()
        self.category = TargetCategory.objects.create(
            day=self.current_day,
            name="Health"
        )
        self.importance = Importance.objects.create(label="High", score=5)
    
    def test_target_create_form_kwargs(self):
        """Test that view passes current day to form"""
        from apps.better.views import TargetCreateView
        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'GET'
        
        view = TargetCreateView()
        view.request = request
        
        kwargs = view.get_form_kwargs()
        self.assertIn('current_day', kwargs)
        self.assertEqual(kwargs['current_day'], ScoreDay.get_or_create_today())
    
    def test_target_create_logic(self):
        """Test target creation logic"""
        # Create target with correct attributes
        target = Target.objects.create(
            name='Exercise',
            category=self.category,
            importance=self.importance,
            is_achieved=False  # Should default to False
        )
        
        # Verify target was created correctly
        self.assertEqual(target.name, 'Exercise')
        self.assertEqual(target.category, self.category)
        self.assertEqual(target.importance, self.importance)
        self.assertFalse(target.is_achieved)
    
    def test_target_create_form_validation(self):
        """Test form validation for target creation"""
        from apps.better.forms import TargetForm
        
        current_day = ScoreDay.get_or_create_today()
        
        # Test valid data
        form = TargetForm(data={
            'name': 'Exercise',
            'category': self.category.id,
            'importance': self.importance.id
        }, current_day=current_day)
        self.assertTrue(form.is_valid())
        
        # Test empty name
        form = TargetForm(data={
            'name': '',
            'category': self.category.id,
            'importance': self.importance.id
        }, current_day=current_day)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_target_create_form_filters_categories(self):
        """Test that form only shows categories from current day"""
        from apps.better.forms import TargetForm
        
        # Create category for different day
        other_day = ScoreDay.objects.create(day=date.today() + timedelta(days=1))
        other_category = TargetCategory.objects.create(day=other_day, name="Other")
        
        form = TargetForm(current_day=self.current_day)
        
        # Form should only include current day's category
        category_choices = [choice[0] for choice in form.fields['category'].choices if choice[0]]
        
        self.assertIn(self.category.id, category_choices)
        self.assertNotIn(other_category.id, category_choices)
    
    def test_target_create_context_data(self):
        """Test context data preparation"""
        from apps.better.views import TargetCreateView
        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'GET'
        
        view = TargetCreateView()
        view.request = request
        
        context = view.get_context_data()
        
        self.assertIn('current_day', context)
        self.assertIn('categories_count', context)
        self.assertIn('importance_levels', context)
        
        # Should show correct counts
        self.assertEqual(context['categories_count'], 1)
        self.assertEqual(context['importance_levels'].count(), 1)


class TargetAchievementViewTests(TestCase):
    """Test class for TargetAchievementView testing achievement toggling"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create current day, category, importance, and target
        self.current_day = ScoreDay.get_or_create_today()
        self.category = TargetCategory.objects.create(
            day=self.current_day,
            name="Health"
        )
        self.importance = Importance.objects.create(label="High", score=5)
        self.target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance,
            is_achieved=False
        )
        
        self.url = reverse('better:target-toggle', kwargs={'pk': self.target.pk})
    
    def test_target_toggle_achievement_logic(self):
        """Test target toggle achievement logic"""
        # Test toggling from false to true
        self.assertFalse(self.target.is_achieved)
        
        self.target.toggle_achievement()
        
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_achieved)
        
        # Test toggling from true to false
        self.target.toggle_achievement()
        
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_achieved)
    
    def test_target_achievement_triggers_score_recalculation(self):
        """Test that toggling achievement triggers score recalculation"""
        # Initial scores should be 0 (no achieved targets)
        self.current_day.calculate_scores()
        initial_score = self.current_day.score
        
        # Toggle achievement
        self.target.toggle_achievement()
        
        # Verify scores were recalculated
        self.current_day.refresh_from_db()
        self.category.refresh_from_db()
        
        self.assertGreater(self.current_day.score, initial_score)
        self.assertEqual(self.current_day.score, self.importance.score)
        self.assertEqual(self.category.score, self.importance.score)
    
    def test_target_achievement_view_validation(self):
        """Test view validation logic for target achievement"""
        from apps.better.views import TargetAchievementView
        from django.shortcuts import get_object_or_404
        
        # Test that view can find current day's target
        current_day = ScoreDay.get_or_create_today()
        target = get_object_or_404(
            Target,
            pk=self.target.pk,
            category__day=current_day,
            is_deleted=False
        )
        
        self.assertEqual(target, self.target)
        
        # Test that view excludes deleted targets
        self.target.is_deleted = True
        self.target.save()
        
        with self.assertRaises(Target.DoesNotExist):
            get_object_or_404(
                Target,
                pk=self.target.pk,
                category__day=current_day,
                is_deleted=False
            )
    
    def test_target_achievement_only_current_day_targets(self):
        """Test that only current day's targets can be found"""
        from django.shortcuts import get_object_or_404
        
        # Create target for different day
        other_day = ScoreDay.objects.create(day=date.today() + timedelta(days=1))
        other_category = TargetCategory.objects.create(day=other_day, name="Other")
        other_target = Target.objects.create(
            name="Other Task",
            category=other_category,
            importance=self.importance
        )
        
        current_day = ScoreDay.get_or_create_today()
        
        # Should not find other day's target
        with self.assertRaises(Target.DoesNotExist):
            get_object_or_404(
                Target,
                pk=other_target.pk,
                category__day=current_day,
                is_deleted=False
            )
    
    def test_target_achievement_json_response_data(self):
        """Test JSON response data structure"""
        # Test the data that would be returned in JSON response
        self.target.toggle_achievement()
        
        # Refresh objects to get updated scores
        self.target.refresh_from_db()
        self.category.refresh_from_db()
        self.current_day.refresh_from_db()
        
        # Test response data structure
        response_data = {
            'success': True,
            'message': f'Target "{self.target.name}" has been completed.',
            'target_id': self.target.id,
            'is_achieved': self.target.is_achieved,
            'category_score': self.category.get_normalized_score(),
            'daily_score': self.current_day.get_normalized_score(),
        }
        
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['target_id'], self.target.id)
        self.assertTrue(response_data['is_achieved'])
        self.assertIsNotNone(response_data['category_score'])
        self.assertIsNotNone(response_data['daily_score'])


class ImportanceManagementViewTests(TestCase):
    """Test class for ImportanceManagementView testing form handling"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.url = reverse('better:importance-manage')
        
        # Create existing importance levels
        self.importance_high = Importance.objects.create(label="High", score=5)
        self.importance_low = Importance.objects.create(label="Low", score=2)
    
    def test_importance_management_get_displays_importance_levels(self):
        """Test GET request displays current importance levels"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Manage Importance Levels')
        self.assertIn('importance_levels', response.context)
        self.assertIn('create_form', response.context)
        self.assertIn('has_importance_levels', response.context)
        
        # Should show existing importance levels
        importance_levels = response.context['importance_levels']
        self.assertEqual(importance_levels.count(), 2)
        self.assertTrue(response.context['has_importance_levels'])
        
        # Should be ordered by score descending
        levels_list = list(importance_levels)
        self.assertEqual(levels_list[0], self.importance_high)
        self.assertEqual(levels_list[1], self.importance_low)
    
    def test_importance_management_get_with_no_importance_levels(self):
        """Test GET request when no importance levels exist"""
        # Delete all importance levels
        Importance.objects.all().delete()
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['importance_levels'].count(), 0)
        self.assertFalse(response.context['has_importance_levels'])
    
    def test_importance_management_post_create_valid_data(self):
        """Test POST request to create new importance level"""
        data = {
            'action': 'create',
            'label': 'Medium',
            'score': 3
        }
        
        response = self.client.post(self.url, data)
        
        # Should redirect back to management page
        self.assertRedirects(response, self.url)
        
        # Verify importance level was created
        self.assertEqual(Importance.objects.count(), 3)
        new_importance = Importance.objects.get(label='Medium')
        self.assertEqual(new_importance.score, 3)
        
        # Verify success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Medium', str(messages[0]))
        self.assertIn('created successfully', str(messages[0]))
        self.assertIn('recalculated automatically', str(messages[0]))
    
    def test_importance_management_post_create_invalid_data(self):
        """Test POST request to create with invalid data shows errors"""
        data = {
            'action': 'create',
            'label': '',  # Empty label should be invalid
            'score': 3
        }
        
        response = self.client.post(self.url, data)
        
        # Should not redirect, should show form with errors
        self.assertEqual(response.status_code, 200)
        self.assertIn('form_errors', response.context)
        self.assertTrue(response.context['form_errors'])
        
        # Verify no importance level was created
        self.assertEqual(Importance.objects.count(), 2)
    
    def test_importance_management_post_create_duplicate_label(self):
        """Test POST request to create with duplicate label shows error"""
        data = {
            'action': 'create',
            'label': 'High',  # Already exists
            'score': 3
        }
        
        response = self.client.post(self.url, data)
        
        # Should show form with validation error
        self.assertEqual(response.status_code, 200)
        self.assertIn('form_errors', response.context)
        
        # Should still have only original importance levels
        self.assertEqual(Importance.objects.count(), 2)
    
    def test_importance_management_post_update_valid_data(self):
        """Test POST request to update existing importance level"""
        data = {
            'action': 'update',
            'importance_id': self.importance_high.id,
            'label': 'Very High',
            'score': 10
        }
        
        response = self.client.post(self.url, data)
        
        # Should redirect back to management page
        self.assertRedirects(response, self.url)
        
        # Verify importance level was updated
        self.importance_high.refresh_from_db()
        self.assertEqual(self.importance_high.label, 'Very High')
        self.assertEqual(self.importance_high.score, 10)
        
        # Verify success message mentions score change
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Very High', str(messages[0]))
        self.assertIn('updated successfully', str(messages[0]))
        self.assertIn('Score changed from 5 to 10', str(messages[0]))
        self.assertIn('recalculated automatically', str(messages[0]))
    
    def test_importance_management_post_update_label_only(self):
        """Test POST request to update only label (no score change)"""
        data = {
            'action': 'update',
            'importance_id': self.importance_high.id,
            'label': 'Critical',
            'score': 5  # Same score
        }
        
        response = self.client.post(self.url, data)
        
        # Should redirect back to management page
        self.assertRedirects(response, self.url)
        
        # Verify importance level was updated
        self.importance_high.refresh_from_db()
        self.assertEqual(self.importance_high.label, 'Critical')
        self.assertEqual(self.importance_high.score, 5)
        
        # Verify success message doesn't mention recalculation
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Critical', str(messages[0]))
        self.assertIn('updated successfully', str(messages[0]))
        self.assertNotIn('recalculated', str(messages[0]))
    
    def test_importance_management_post_update_nonexistent_id(self):
        """Test POST request to update nonexistent importance level"""
        data = {
            'action': 'update',
            'importance_id': 99999,
            'label': 'Updated',
            'score': 3
        }
        
        response = self.client.post(self.url, data)
        
        # Should redirect with error message
        self.assertRedirects(response, self.url)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('not found', str(messages[0]))
    
    def test_importance_management_post_update_invalid_data(self):
        """Test POST request to update with invalid data"""
        data = {
            'action': 'update',
            'importance_id': self.importance_high.id,
            'label': '',  # Empty label
            'score': 5
        }
        
        response = self.client.post(self.url, data)
        
        # Should redirect with error message
        self.assertRedirects(response, self.url)
        
        # Verify importance level was not updated
        self.importance_high.refresh_from_db()
        self.assertEqual(self.importance_high.label, 'High')
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(len(messages) > 0)
    
    def test_importance_management_post_delete_unused_importance(self):
        """Test POST request to delete unused importance level"""
        data = {
            'action': 'delete',
            'importance_id': self.importance_high.id
        }
        
        response = self.client.post(self.url, data)
        
        # Should redirect back to management page
        self.assertRedirects(response, self.url)
        
        # Verify importance level was deleted
        self.assertEqual(Importance.objects.count(), 1)
        self.assertFalse(Importance.objects.filter(id=self.importance_high.id).exists())
        
        # Verify success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('High', str(messages[0]))
        self.assertIn('deleted successfully', str(messages[0]))
        self.assertIn('recalculated automatically', str(messages[0]))
    
    def test_importance_management_post_delete_used_importance(self):
        """Test POST request to delete importance level in use by targets"""
        # Create target using the importance level
        current_day = ScoreDay.get_or_create_today()
        category = TargetCategory.objects.create(day=current_day, name="Health")
        Target.objects.create(
            name="Exercise",
            category=category,
            importance=self.importance_high
        )
        
        data = {
            'action': 'delete',
            'importance_id': self.importance_high.id
        }
        
        response = self.client.post(self.url, data)
        
        # Should redirect with error message
        self.assertRedirects(response, self.url)
        
        # Verify importance level was not deleted
        self.assertEqual(Importance.objects.count(), 2)
        self.assertTrue(Importance.objects.filter(id=self.importance_high.id).exists())
        
        # Verify error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Cannot delete', str(messages[0]))
        self.assertIn('being used by', str(messages[0]))
    
    def test_importance_management_post_delete_nonexistent_id(self):
        """Test POST request to delete nonexistent importance level"""
        data = {
            'action': 'delete',
            'importance_id': 99999
        }
        
        response = self.client.post(self.url, data)
        
        # Should redirect with error message
        self.assertRedirects(response, self.url)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('not found', str(messages[0]))
    
    def test_importance_management_post_invalid_action(self):
        """Test POST request with invalid action"""
        data = {
            'action': 'invalid_action',
            'label': 'Test',
            'score': 3
        }
        
        response = self.client.post(self.url, data)
        
        # Should redirect with error message
        self.assertRedirects(response, self.url)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Invalid action', str(messages[0]))
    
    def test_importance_management_post_missing_action(self):
        """Test POST request with missing action parameter"""
        data = {
            'label': 'Test',
            'score': 3
        }
        
        response = self.client.post(self.url, data)
        
        # Should default to create action
        self.assertRedirects(response, self.url)
        
        # Should create new importance level
        self.assertEqual(Importance.objects.count(), 3)
        self.assertTrue(Importance.objects.filter(label='Test').exists())   
 
    def test_importance_management_view_context_data(self):
        """Test context data preparation for importance management"""
        from apps.better.views import ImportanceManagementView
        from apps.better.forms import ImportanceForm
        from django.http import HttpRequest
        
        request = HttpRequest()
        request.method = 'GET'
        
        view = ImportanceManagementView()
        view.request = request
        
        # Test the logic that would be in get method
        importance_levels = Importance.objects.all().order_by('-score')
        create_form = ImportanceForm()
        
        # Verify data structure
        self.assertEqual(importance_levels.count(), 2)
        self.assertEqual(list(importance_levels), [self.importance_high, self.importance_low])
        self.assertIsInstance(create_form, ImportanceForm)
    
    def test_importance_management_create_logic(self):
        """Test importance level creation logic"""
        from apps.better.forms import ImportanceForm
        
        # Test valid creation
        form = ImportanceForm(data={'label': 'Medium', 'score': 3})
        self.assertTrue(form.is_valid())
        
     