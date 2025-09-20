from datetime import date, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.better.models import Target, Importance, ScoreDay, TargetCategory


class ImportanceModelTests(TestCase):
    """Test class for Importance model testing validation"""

    def test_importance_creation_with_valid_data(self):
        """Test creating importance with valid label and score"""
        importance = Importance.objects.create(
            label="Critical",
            score=5
        )
        self.assertEqual(importance.label, "Critical")
        self.assertEqual(importance.score, 5)
        self.assertEqual(str(importance), "Critical (5)")

    def test_importance_unique_label_constraint(self):
        """Test that importance labels must be unique"""
        Importance.objects.create(label="Important", score=3)

        with self.assertRaises(IntegrityError):
            Importance.objects.create(label="Important", score=4)

    def test_importance_score_positive_validation(self):
        """Test that importance score must be positive"""
        importance = Importance(label="Invalid", score=0)

        with self.assertRaises(ValidationError):
            importance.full_clean()

    def test_importance_score_negative_validation(self):
        """Test that importance score cannot be negative"""
        importance = Importance(label="Invalid", score=-1)

        with self.assertRaises(ValidationError):
            importance.full_clean()

    def test_get_max_score_with_importances(self):
        """Test get_max_score returns highest importance score"""
        Importance.objects.create(label="Low", score=1)
        Importance.objects.create(label="High", score=5)
        Importance.objects.create(label="Medium", score=3)

        max_score = Importance.get_max_score()
        self.assertEqual(max_score, 5)

    def test_get_max_score_with_no_importances(self):
        """Test get_max_score returns 0 when no importances exist"""
        max_score = Importance.get_max_score()
        self.assertEqual(max_score, 0)

    def test_importance_ordering(self):
        """Test that importances are ordered by score descending"""
        low = Importance.objects.create(label="Low", score=1)
        high = Importance.objects.create(label="High", score=5)
        medium = Importance.objects.create(label="Medium", score=3)

        importances = list(Importance.objects.all())
        self.assertEqual(importances, [high, medium, low])


class ScoreDayModelTests(TestCase):
    """Test class for ScoreDay model testing score calculations"""

    def setUp(self):
        """Set up test data"""
        self.importance_high = Importance.objects.create(label="High", score=5)
        self.importance_low = Importance.objects.create(label="Low", score=2)

        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)

    def test_scoreday_creation(self):
        """Test creating a ScoreDay with valid data"""
        score_day = ScoreDay.objects.create(day=self.today)

        self.assertEqual(score_day.day, self.today)
        self.assertIsNone(score_day.score)
        self.assertIsNone(score_day.max_score)
        self.assertFalse(score_day.is_deleted)
        self.assertEqual(str(score_day), f"ScoreDay {self.today}")

    def test_scoreday_unique_day_constraint(self):
        """Test that only one ScoreDay can exist per day"""
        ScoreDay.objects.create(day=self.today)

        with self.assertRaises(IntegrityError):
            ScoreDay.objects.create(day=self.today)

    def test_calculate_scores_with_no_categories(self):
        """Test score calculation with no categories"""
        score_day = ScoreDay.objects.create(day=self.today)
        score_day.calculate_scores()

        self.assertEqual(score_day.score, 0)
        self.assertEqual(score_day.max_score, 0)

    def test_calculate_scores_with_categories_and_targets(self):
        """Test score calculation with categories and targets"""
        score_day = ScoreDay.objects.create(day=self.today)

        # Create category with targets
        category = TargetCategory.objects.create(
            day=score_day,
            name="Health"
        )

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

        score_day.calculate_scores()

        # Expected: max_score = 2 targets * 5 (highest importance) = 10
        # Expected: score = 1 achieved target * 5 (its importance) = 5
        self.assertEqual(score_day.max_score, 10)
        self.assertEqual(score_day.score, 5)

    def test_calculate_scores_with_multiple_categories(self):
        """Test score calculation with multiple categories"""
        score_day = ScoreDay.objects.create(day=self.today)

        # Category 1
        category1 = TargetCategory.objects.create(day=score_day, name="Health")
        Target.objects.create(
            name="Exercise",
            category=category1,
            importance=self.importance_high,
            is_achieved=True
        )

        # Category 2
        category2 = TargetCategory.objects.create(day=score_day, name="Work")
        Target.objects.create(
            name="Complete task",
            category=category2,
            importance=self.importance_low,
            is_achieved=True
        )

        score_day.calculate_scores()

        # Expected: max_score = (1*5) + (1*5) = 10
        # Expected: score = 5 + 2 = 7
        self.assertEqual(score_day.max_score, 10)
        self.assertEqual(score_day.score, 7)

    def test_get_normalized_score_with_zero_max_score(self):
        """Test normalized score returns 0 when max_score is 0"""
        score_day = ScoreDay.objects.create(day=self.today, score=0, max_score=0)
        normalized = score_day.get_normalized_score()
        self.assertEqual(normalized, 0)

    def test_get_normalized_score_with_small_max_score(self):
        """Test normalized score with factor 10 for small max scores"""
        score_day = ScoreDay.objects.create(day=self.today, score=3, max_score=10)
        normalized = score_day.get_normalized_score()
        # 30% * 10 / 100 = 3.0
        self.assertEqual(normalized, 3.0)

    def test_get_normalized_score_with_large_max_score(self):
        """Test normalized score with factor 100 for large max scores"""
        score_day = ScoreDay.objects.create(day=self.today, score=75, max_score=150)
        normalized = score_day.get_normalized_score()
        # 50% * 100 / 100 = 50.0
        self.assertEqual(normalized, 50.0)

    def test_copy_previous_day_categories_with_no_previous_day(self):
        """Test copying categories when no previous day exists"""
        score_day = ScoreDay.objects.create(day=self.today)
        score_day.copy_previous_day_categories()

        # Should not create any categories
        self.assertEqual(score_day.categories.count(), 0)

    def test_copy_previous_day_categories_with_previous_day(self):
        """Test copying categories from previous day"""
        # Create previous day with categories and targets
        prev_day = ScoreDay.objects.create(day=self.yesterday)
        prev_category = TargetCategory.objects.create(
            day=prev_day,
            name="Health"
        )
        prev_target = Target.objects.create(
            name="Exercise",
            category=prev_category,
            importance=self.importance_high,
            is_achieved=True
        )

        # Create current day and copy
        current_day = ScoreDay.objects.create(day=self.today)
        current_day.copy_previous_day_categories()

        # Verify category was copied
        self.assertEqual(current_day.categories.count(), 1)
        new_category = current_day.categories.first()
        self.assertEqual(new_category.name, "Health")
        # Scores should be calculated automatically, so they won't be None
        self.assertEqual(new_category.score, 0)  # No achieved targets yet
        self.assertEqual(new_category.max_score, self.importance_high.score)  # 1 target * high importance

        # Verify target was copied with reset achievement
        self.assertEqual(new_category.targets.count(), 1)
        new_target = new_category.targets.first()
        self.assertEqual(new_target.name, "Exercise")
        self.assertEqual(new_target.importance, self.importance_high)
        self.assertFalse(new_target.is_achieved)  # Should be reset

    @patch('django.utils.timezone.now')
    def test_get_or_create_today_creates_new_day(self, mock_now):
        """Test get_or_create_today creates new ScoreDay for today"""
        from datetime import datetime
        mock_datetime = datetime.combine(self.today, datetime.min.time())
        mock_now.return_value = mock_datetime

        score_day = ScoreDay.get_or_create_today()

        self.assertEqual(score_day.day, self.today)
        self.assertEqual(ScoreDay.objects.count(), 1)

    @patch('django.utils.timezone.now')
    def test_get_or_create_today_returns_existing_day(self, mock_now):
        """Test get_or_create_today returns existing ScoreDay"""
        from datetime import datetime
        mock_datetime = datetime.combine(self.today, datetime.min.time())
        mock_now.return_value = mock_datetime

        existing_day = ScoreDay.objects.create(day=self.today)
        score_day = ScoreDay.get_or_create_today()

        self.assertEqual(score_day.id, existing_day.id)
        self.assertEqual(ScoreDay.objects.count(), 1)


class TargetCategoryModelTests(TestCase):
    """Test class for TargetCategory model testing category scoring"""

    def setUp(self):
        """Set up test data"""
        self.importance_high = Importance.objects.create(label="High", score=5)
        self.importance_low = Importance.objects.create(label="Low", score=2)

        self.score_day = ScoreDay.objects.create(day=date.today())

    def test_target_category_creation(self):
        """Test creating TargetCategory with valid data"""
        category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health"
        )

        self.assertEqual(category.day, self.score_day)
        self.assertEqual(category.name, "Health")
        self.assertIsNone(category.score)
        self.assertIsNone(category.max_score)
        self.assertFalse(category.is_deleted)
        self.assertEqual(str(category), f"Health ({self.score_day.day})")

    def test_target_category_unique_name_per_day(self):
        """Test that category names must be unique per day"""
        TargetCategory.objects.create(day=self.score_day, name="Health")

        with self.assertRaises(IntegrityError):
            TargetCategory.objects.create(day=self.score_day, name="Health")

    def test_target_category_same_name_different_days(self):
        """Test that same category name can exist on different days"""
        other_day = ScoreDay.objects.create(day=date.today() + timedelta(days=1))

        category1 = TargetCategory.objects.create(day=self.score_day, name="Health")
        category2 = TargetCategory.objects.create(day=other_day, name="Health")

        self.assertNotEqual(category1.id, category2.id)

    def test_calculate_scores_with_no_targets(self):
        """Test score calculation with no targets"""
        category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health"
        )

        category.calculate_scores()

        self.assertEqual(category.score, 0)
        self.assertEqual(category.max_score, 0)

    def test_calculate_scores_with_targets_none_achieved(self):
        """Test score calculation with targets but none achieved"""
        category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health"
        )

        Target.objects.create(
            name="Exercise",
            category=category,
            importance=self.importance_high,
            is_achieved=False
        )

        Target.objects.create(
            name="Meditate",
            category=category,
            importance=self.importance_low,
            is_achieved=False
        )

        category.calculate_scores()

        # Expected: max_score = 2 targets * 5 (highest importance) = 10
        # Expected: score = 0 (no achieved targets)
        self.assertEqual(category.max_score, 10)
        self.assertEqual(category.score, 0)

    def test_calculate_scores_with_some_targets_achieved(self):
        """Test score calculation with some targets achieved"""
        category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health"
        )

        Target.objects.create(
            name="Exercise",
            category=category,
            importance=self.importance_high,
            is_achieved=True
        )

        Target.objects.create(
            name="Meditate",
            category=category,
            importance=self.importance_low,
            is_achieved=False
        )

        category.calculate_scores()

        # Expected: max_score = 2 targets * 5 (highest importance) = 10
        # Expected: score = 1 achieved target * 5 (its importance) = 5
        self.assertEqual(category.max_score, 10)
        self.assertEqual(category.score, 5)

    def test_calculate_scores_with_all_targets_achieved(self):
        """Test score calculation with all targets achieved"""
        category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health"
        )

        Target.objects.create(
            name="Exercise",
            category=category,
            importance=self.importance_high,
            is_achieved=True
        )

        Target.objects.create(
            name="Meditate",
            category=category,
            importance=self.importance_low,
            is_achieved=True
        )

        category.calculate_scores()

        # Expected: max_score = 2 targets * 5 (highest importance) = 10
        # Expected: score = 5 + 2 = 7
        self.assertEqual(category.max_score, 10)
        self.assertEqual(category.score, 7)

    def test_calculate_scores_excludes_deleted_targets(self):
        """Test that deleted targets are excluded from calculations"""
        category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health"
        )

        # Active target
        Target.objects.create(
            name="Exercise",
            category=category,
            importance=self.importance_high,
            is_achieved=True
        )

        # Deleted target
        Target.objects.create(
            name="Deleted",
            category=category,
            importance=self.importance_low,
            is_achieved=True,
            is_deleted=True
        )

        category.calculate_scores()

        # Should only count the active target
        # Expected: max_score = 1 target * 5 = 5
        # Expected: score = 1 achieved target * 5 = 5
        self.assertEqual(category.max_score, 5)
        self.assertEqual(category.score, 5)

    def test_get_normalized_score_with_zero_max_score(self):
        """Test normalized score returns 0 when max_score is 0"""
        category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health",
            score=0,
            max_score=0
        )

        normalized = category.get_normalized_score()
        self.assertEqual(normalized, 0)

    def test_get_normalized_score_with_small_max_score(self):
        """Test normalized score with factor 10 for small max scores"""
        category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health",
            score=3,
            max_score=10
        )

        normalized = category.get_normalized_score()
        # 30% * 10 / 100 = 3.0
        self.assertEqual(normalized, 3.0)

    def test_get_normalized_score_with_large_max_score(self):
        """Test normalized score with factor 100 for large max scores"""
        category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health",
            score=75,
            max_score=150
        )

        normalized = category.get_normalized_score()
        # 50% * 100 / 100 = 50.0
        self.assertEqual(normalized, 50.0)


class TargetModelTests(TestCase):
    """Test class for Target model testing achievement logic"""

    def setUp(self):
        """Set up test data"""
        self.importance_high = Importance.objects.create(label="High", score=5)
        self.importance_low = Importance.objects.create(label="Low", score=2)

        self.score_day = ScoreDay.objects.create(day=date.today())
        self.category = TargetCategory.objects.create(
            day=self.score_day,
            name="Health"
        )

    def test_target_creation(self):
        """Test creating Target with valid data"""
        target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high
        )

        self.assertEqual(target.name, "Exercise")
        self.assertEqual(target.category, self.category)
        self.assertEqual(target.importance, self.importance_high)
        self.assertFalse(target.is_achieved)
        self.assertFalse(target.is_deleted)
        self.assertEqual(str(target), "Exercise (Health)")

    def test_target_default_is_achieved_false(self):
        """Test that targets default to not achieved"""
        target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high
        )

        self.assertFalse(target.is_achieved)

    def test_toggle_achievement_from_false_to_true(self):
        """Test toggling achievement from false to true"""
        target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=False
        )

        target.toggle_achievement()

        self.assertTrue(target.is_achieved)

    def test_toggle_achievement_from_true_to_false(self):
        """Test toggling achievement from true to false"""
        target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=True
        )

        target.toggle_achievement()

        self.assertFalse(target.is_achieved)

    def test_toggle_achievement_triggers_category_recalculation(self):
        """Test that toggling achievement triggers category score recalculation"""
        target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=False
        )

        # Initially category should have 0 score
        self.category.calculate_scores()
        initial_score = self.category.score

        # Toggle achievement
        target.toggle_achievement()

        # Refresh category from database
        self.category.refresh_from_db()

        # Category score should have increased
        self.assertGreater(self.category.score, initial_score)
        self.assertEqual(self.category.score, self.importance_high.score)

    def test_toggle_achievement_triggers_day_recalculation(self):
        """Test that toggling achievement triggers day score recalculation"""
        target = Target.objects.create(
            name="Exercise",
            category=self.category,
            importance=self.importance_high,
            is_achieved=False
        )

        # Initially day should have 0 score
        self.score_day.calculate_scores()
        initial_score = self.score_day.score

        # Toggle achievement
        target.toggle_achievement()

        # Refresh day from database
        self.score_day.refresh_from_db()

        # Day score should have increased
        self.assertGreater(self.score_day.score, initial_score)
        self.assertEqual(self.score_day.score, self.importance_high.score)

    def test_target_ordering(self):
        """Test that targets are ordered by importance score descending, then name"""
        target_low = Target.objects.create(
            name="B Task",
            category=self.category,
            importance=self.importance_low
        )

        target_high = Target.objects.create(
            name="A Task",
            category=self.category,
            importance=self.importance_high
        )

        target_high2 = Target.objects.create(
            name="C Task",
            category=self.category,
            importance=self.importance_high
        )

        targets = list(Target.objects.all())
        # Should be ordered by importance desc, then name asc
        expected_order = [target_high, target_high2, target_low]
        self.assertEqual(targets, expected_order)
