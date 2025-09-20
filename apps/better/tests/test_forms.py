from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta

from ..models import ScoreDay, TargetCategory, Target, Importance
from ..forms import TargetCategoryForm, TargetForm, TargetAchievementForm, ImportanceForm, SleepWakeTimeForm


class TargetCategoryFormTests(TestCase):
    """Test TargetCategoryForm validation and functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.current_day = ScoreDay.objects.create(day=date.today())
    
    def test_valid_form_data(self):
        """Test form with valid data"""
        form_data = {
            'name': 'Health',
            'description': 'Health related targets'
        }
        form = TargetCategoryForm(data=form_data, current_day=self.current_day)
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['name'], 'Health')
        self.assertEqual(form.cleaned_data['description'], 'Health related targets')
    
    def test_form_without_name(self):
        """Test form validation fails without name"""
        form_data = {
            'description': 'Health related targets'
        }
        form = TargetCategoryForm(data=form_data, current_day=self.current_day)
        
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_form_with_empty_name(self):
        """Test form validation fails with empty name"""
        form_data = {
            'name': '',
            'description': 'Health related targets'
        }
        form = TargetCategoryForm(data=form_data, current_day=self.current_day)
        
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_form_with_duplicate_name_same_day(self):
        """Test form validation fails with duplicate name on same day"""
        # Create existing category
        TargetCategory.objects.create(
            day=self.current_day,
            name='Health'
        )
        
        form_data = {
            'name': 'Health',
            'description': 'Duplicate health category'
        }
        form = TargetCategoryForm(data=form_data, current_day=self.current_day)
        
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_form_with_same_name_different_day(self):
        """Test form allows same name on different day"""
        # Create category on different day
        other_day = ScoreDay.objects.create(day=date.today() + timedelta(days=1))
        TargetCategory.objects.create(
            day=other_day,
            name='Health'
        )
        
        form_data = {
            'name': 'Health',
            'description': 'Health category for today'
        }
        form = TargetCategoryForm(data=form_data, current_day=self.current_day)
        
        self.assertTrue(form.is_valid())
    
    def test_form_save_creates_category(self):
        """Test form save creates category correctly"""
        form_data = {
            'name': 'Health',
            'description': 'Health related targets'
        }
        form = TargetCategoryForm(data=form_data, current_day=self.current_day)
        
        self.assertTrue(form.is_valid())
        category = form.save(commit=False)
        category.day = self.current_day
        category.save()
        
        self.assertEqual(category.name, 'Health')
        self.assertEqual(category.description, 'Health related targets')
        self.assertEqual(category.day, self.current_day)


class TargetFormTests(TestCase):
    """Test TargetForm validation and functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.current_day = ScoreDay.objects.create(day=date.today())
        self.category = TargetCategory.objects.create(
            day=self.current_day,
            name='Health'
        )
        self.importance = Importance.objects.create(label="High", score=5)
    
    def test_valid_form_data(self):
        """Test form with valid data"""
        form_data = {
            'name': 'Exercise',
            'category': self.category.id,
            'importance': self.importance.id
        }
        form = TargetForm(data=form_data, current_day=self.current_day)
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['name'], 'Exercise')
        self.assertEqual(form.cleaned_data['category'], self.category)
        self.assertEqual(form.cleaned_data['importance'], self.importance)
    
    def test_form_without_name(self):
        """Test form validation fails without name"""
        form_data = {
            'category': self.category.id,
            'importance': self.importance.id
        }
        form = TargetForm(data=form_data, current_day=self.current_day)
        
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_form_without_category(self):
        """Test form validation fails without category"""
        form_data = {
            'name': 'Exercise',
            'importance': self.importance.id
        }
        form = TargetForm(data=form_data, current_day=self.current_day)
        
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)
    
    def test_form_without_importance(self):
        """Test form validation fails without importance"""
        form_data = {
            'name': 'Exercise',
            'category': self.category.id
        }
        form = TargetForm(data=form_data, current_day=self.current_day)
        
        self.assertFalse(form.is_valid())
        self.assertIn('importance', form.errors)
    
    def test_form_filters_categories_by_current_day(self):
        """Test form only shows categories from current day"""
        # Create category on different day
        other_day = ScoreDay.objects.create(day=date.today() + timedelta(days=1))
        other_category = TargetCategory.objects.create(
            day=other_day,
            name='Work'
        )
        
        form = TargetForm(current_day=self.current_day)
        
        # Should only include current day's categories
        category_choices = [choice[0] for choice in form.fields['category'].choices if choice[0]]
        self.assertIn(self.category.id, category_choices)
        self.assertNotIn(other_category.id, category_choices)
    
    def test_form_excludes_deleted_categories(self):
        """Test form excludes soft-deleted categories"""
        # Create deleted category
        deleted_category = TargetCategory.objects.create(
            day=self.current_day,
            name='Deleted',
            is_deleted=True
        )
        
        form = TargetForm(current_day=self.current_day)
        
        # Should not include deleted categories
        category_choices = [choice[0] for choice in form.fields['category'].choices if choice[0]]
        self.assertIn(self.category.id, category_choices)
        self.assertNotIn(deleted_category.id, category_choices)
    
    def test_form_save_creates_target(self):
        """Test form save creates target correctly"""
        form_data = {
            'name': 'Exercise',
            'category': self.category.id,
            'importance': self.importance.id
        }
        form = TargetForm(data=form_data, current_day=self.current_day)
        
        self.assertTrue(form.is_valid())
        target = form.save()
        
        self.assertEqual(target.name, 'Exercise')
        self.assertEqual(target.category, self.category)
        self.assertEqual(target.importance, self.importance)
        self.assertFalse(target.is_achieved)  # Default value


class ImportanceFormTests(TestCase):
    """Test ImportanceForm validation and functionality"""
    
    def test_valid_form_data(self):
        """Test form with valid data"""
        form_data = {
            'label': 'Critical',
            'score': 5
        }
        form = ImportanceForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['label'], 'Critical')
        self.assertEqual(form.cleaned_data['score'], 5)
    
    def test_form_without_label(self):
        """Test form validation fails without label"""
        form_data = {
            'score': 5
        }
        form = ImportanceForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('label', form.errors)
    
    def test_form_without_score(self):
        """Test form validation fails without score"""
        form_data = {
            'label': 'Critical'
        }
        form = ImportanceForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('score', form.errors)
    
    def test_form_with_zero_score(self):
        """Test form validation fails with zero score"""
        form_data = {
            'label': 'Critical',
            'score': 0
        }
        form = ImportanceForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('score', form.errors)
    
    def test_form_with_negative_score(self):
        """Test form validation fails with negative score"""
        form_data = {
            'label': 'Critical',
            'score': -1
        }
        form = ImportanceForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('score', form.errors)
    
    def test_form_with_duplicate_label(self):
        """Test form validation fails with duplicate label"""
        # Create existing importance
        Importance.objects.create(label='Critical', score=5)
        
        form_data = {
            'label': 'Critical',
            'score': 3
        }
        form = ImportanceForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('label', form.errors)
    
    def test_form_save_creates_importance(self):
        """Test form save creates importance correctly"""
        form_data = {
            'label': 'Critical',
            'score': 5
        }
        form = ImportanceForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        importance = form.save()
        
        self.assertEqual(importance.label, 'Critical')
        self.assertEqual(importance.score, 5)


class SleepWakeTimeFormTests(TestCase):
    """Test SleepWakeTimeForm validation and functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.score_day = ScoreDay.objects.create(day=date.today())
    
    def test_valid_form_data(self):
        """Test form with valid wake and sleep times"""
        wake_time = timezone.now().replace(hour=7, minute=0, second=0, microsecond=0)
        sleep_time = timezone.now().replace(hour=23, minute=0, second=0, microsecond=0)
        
        form_data = {
            'wake_time': wake_time,
            'sleep_time': sleep_time
        }
        form = SleepWakeTimeForm(data=form_data, instance=self.score_day)
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['wake_time'], wake_time)
        self.assertEqual(form.cleaned_data['sleep_time'], sleep_time)
    
    def test_form_with_only_wake_time(self):
        """Test form with only wake time (sleep time optional)"""
        wake_time = timezone.now().replace(hour=7, minute=0, second=0, microsecond=0)
        
        form_data = {
            'wake_time': wake_time
        }
        form = SleepWakeTimeForm(data=form_data, instance=self.score_day)
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['wake_time'], wake_time)
        self.assertIsNone(form.cleaned_data.get('sleep_time'))
    
    def test_form_with_only_sleep_time(self):
        """Test form with only sleep time (wake time optional)"""
        sleep_time = timezone.now().replace(hour=23, minute=0, second=0, microsecond=0)
        
        form_data = {
            'sleep_time': sleep_time
        }
        form = SleepWakeTimeForm(data=form_data, instance=self.score_day)
        
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data.get('wake_time'))
        self.assertEqual(form.cleaned_data['sleep_time'], sleep_time)
    
    def test_form_with_empty_data(self):
        """Test form with no data (both times optional)"""
        form_data = {}
        form = SleepWakeTimeForm(data=form_data, instance=self.score_day)
        
        self.assertTrue(form.is_valid())
    
    def test_form_save_updates_score_day(self):
        """Test form save updates ScoreDay instance"""
        wake_time = timezone.now().replace(hour=7, minute=0, second=0, microsecond=0)
        sleep_time = timezone.now().replace(hour=23, minute=0, second=0, microsecond=0)
        
        form_data = {
            'wake_time': wake_time,
            'sleep_time': sleep_time
        }
        form = SleepWakeTimeForm(data=form_data, instance=self.score_day)
        
        self.assertTrue(form.is_valid())
        updated_score_day = form.save()
        
        self.assertEqual(updated_score_day.wake_time, wake_time)
        self.assertEqual(updated_score_day.sleep_time, sleep_time)
        
        # Verify in database
        self.score_day.refresh_from_db()
        self.assertEqual(self.score_day.wake_time, wake_time)
        self.assertEqual(self.score_day.sleep_time, sleep_time)


class TargetAchievementFormTests(TestCase):
    """Test TargetAchievementForm validation and functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.importance = Importance.objects.create(label="High", score=5)
        self.current_day = ScoreDay.objects.create(day=date.today())
        self.category = TargetCategory.objects.create(
            day=self.current_day,
            name='Health'
        )
        self.target = Target.objects.create(
            name='Exercise',
            category=self.category,
            importance=self.importance,
            is_achieved=False
        )
    
    def test_form_initialization_with_target(self):
        """Test form initializes correctly with target instance"""
        form = TargetAchievementForm(instance=self.target)
        
        self.assertEqual(form.instance, self.target)
        self.assertFalse(form.initial.get('is_achieved', False))
    
    def test_form_toggle_achievement_to_true(self):
        """Test form can toggle achievement to true"""
        form_data = {
            'is_achieved': True
        }
        form = TargetAchievementForm(data=form_data, instance=self.target)
        
        self.assertTrue(form.is_valid())
        updated_target = form.save()
        
        self.assertTrue(updated_target.is_achieved)
        
        # Verify in database
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_achieved)
    
    def test_form_toggle_achievement_to_false(self):
        """Test form can toggle achievement to false"""
        # Set target as achieved first
        self.target.is_achieved = True
        self.target.save()
        
        form_data = {
            'is_achieved': False
        }
        form = TargetAchievementForm(data=form_data, instance=self.target)
        
        self.assertTrue(form.is_valid())
        updated_target = form.save()
        
        self.assertFalse(updated_target.is_achieved)
        
        # Verify in database
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_achieved)