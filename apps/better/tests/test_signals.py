from django.test import TestCase
from datetime import date, timedelta

from apps.better.models import ScoreDay, TargetCategory, Target, Importance


class TargetSignalTests(TestCase):
    """Test signal-triggered recalculation for Target model"""
    
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
        Target.objects.create(
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
        
        Target.objects.create(
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
    
    def test_deleted_target_excluded_from_recalculation(self):
        """Test that soft-deleted targets are excluded from recalculation"""
        Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=True,
            is_deleted=True  # Soft deleted
        )
        
        # Refresh objects from database
        self.category.refresh_from_db()
        self.score_day.refresh_from_db()
        
        # Scores should be 0 since deleted target is excluded
        self.assertEqual(self.category.score, 0)
        self.assertEqual(self.score_day.score, 0)


class ImportanceSignalTests(TestCase):
    """Test signal-triggered recalculation for Importance model"""
    
    def setUp(self):
        """Set up test data"""
        self.importance_high = Importance.objects.create(label="High", score=5)
        self.importance_low = Importance.objects.create(label="Low", score=2)
        
        # Create multiple days with targets
        self.day1 = ScoreDay.objects.create(day=date.today())
        self.category1 = TargetCategory.objects.create(day=self.day1, name="Health")
        self.target1 = Target.objects.create(
            name="Exercise",
            category=self.category1,
            importance=self.importance_high,
            is_achieved=True
        )
        
        self.day2 = ScoreDay.objects.create(day=date.today() + timedelta(days=1))
        self.category2 = TargetCategory.objects.create(day=self.day2, name="Work")
        self.target2 = Target.objects.create(
            name="Complete task",
            category=self.category2,
            importance=self.importance_high,
            is_achieved=True
        )
    
    def test_importance_save_triggers_global_recalculation(self):
        """Test that saving importance triggers global recalculation"""
        # Get initial scores
        self.day1.refresh_from_db()
        self.day2.refresh_from_db()
        initial_day1_max = self.day1.max_score
        initial_day2_max = self.day2.max_score
        
        # Update importance score (this should trigger global recalculation)
        self.importance_high.score = 10
        self.importance_high.save()
        
        # Refresh all objects from database
        self.day1.refresh_from_db()
        self.day2.refresh_from_db()
        
        # Max scores should have increased for both days
        self.assertGreater(self.day1.max_score, initial_day1_max)
        self.assertGreater(self.day2.max_score, initial_day2_max)
    
    def test_importance_delete_triggers_global_recalculation(self):
        """Test that deleting importance triggers global recalculation"""
        # Create a third importance level
        importance_medium = Importance.objects.create(label="Medium", score=3)
        
        # Create target using medium importance
        Target.objects.create(
            name="Meditate",
            category=self.category1,
            importance=importance_medium,
            is_achieved=True
        )
        
        # Get initial scores
        self.day1.refresh_from_db()
        initial_max_score = self.day1.max_score
        
        # Delete the highest importance (this should trigger recalculation)
        self.importance_high.delete()
        
        # Refresh objects from database
        self.day1.refresh_from_db()
        
        # Max score should have changed (now based on medium importance as highest)
        self.assertNotEqual(self.day1.max_score, initial_max_score)


class TargetCategorySignalTests(TestCase):
    """Test signal-triggered recalculation for TargetCategory model"""
    
    def setUp(self):
        """Set up test data"""
        self.importance = Importance.objects.create(label="High", score=5)
        self.score_day = ScoreDay.objects.create(day=date.today())
        self.category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health"
        )
    
    def test_target_category_save_triggers_day_recalculation(self):
        """Test that saving target category triggers day recalculation"""
        # Create target
        Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance,
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
        # Create target
        Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance,
            is_achieved=True
        )
        
        # Get initial day score
        self.score_day.refresh_from_db()
        initial_score = self.score_day.score
        self.assertGreater(initial_score, 0)
        
        # Delete category
        self.category.delete()
        
        # Refresh day from database
        self.score_day.refresh_from_db()
        
        # Day score should be 0 after category deletion
        self.assertEqual(self.score_day.score, 0)
        self.assertEqual(self.score_day.max_score, 0)
    
    def test_soft_deleted_category_excluded_from_recalculation(self):
        """Test that soft-deleted categories are excluded from recalculation"""
        # Create target
        Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance,
            is_achieved=True
        )
        
        # Mark category as deleted
        self.category.is_deleted = True
        self.category.save()
        
        # Refresh day from database
        self.score_day.refresh_from_db()
        
        # Day score should be 0 since category is soft deleted
        self.assertEqual(self.score_day.score, 0)
        self.assertEqual(self.score_day.max_score, 0)