from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class Importance(models.Model):
    label = models.CharField(max_length=200, unique=True)
    score = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ['-score']

    def __str__(self):
        return f"{self.label} ({self.score})"

    @classmethod
    def get_max_score(cls):
        """Return highest importance score for max calculations"""
        max_importance = cls.objects.aggregate(max_score=models.Max('score'))
        return max_importance['max_score'] or 0


class ScoreDay(BaseModel):
    day = models.DateField(unique=True)
    score = models.PositiveIntegerField(null=True, blank=True)
    max_score = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-day']

    def __str__(self):
        return f"ScoreDay {self.day}"

    def calculate_scores(self):
        """Calculate and update daily scores from target categories"""
        categories = self.categories.filter(is_deleted=False)
        
        # Calculate scores for each category first
        for category in categories:
            category.calculate_scores()
        
        # Calculate daily totals
        totals = categories.aggregate(
            total_score=models.Sum('score'),
            total_max_score=models.Sum('max_score')
        )
        
        self.score = totals['total_score'] or 0
        self.max_score = totals['total_max_score'] or 0
        # Save without triggering signals to prevent recursion
        self.save(update_fields=['score', 'max_score', 'updated_at'])

    def get_normalized_score(self):
        """Return display-friendly normalized score"""
        if not self.max_score or self.max_score == 0:
            return 0
        
        percentage = (self.score / self.max_score) * 100
        
        # Determine normalization factor based on score magnitude
        if self.max_score >= 100:
            factor = 100
        else:
            factor = 10
            
        return round(percentage * factor / 100, 1)

    def copy_previous_day_categories(self):
        """Copy target categories from previous day"""
        previous_day = ScoreDay.objects.filter(
            day__lt=self.day,
            is_deleted=False
        ).order_by('-day').first()
        
        if not previous_day:
            return
        
        previous_categories = previous_day.categories.filter(is_deleted=False)
        
        for prev_category in previous_categories:
            # Create new category for current day
            new_category = TargetCategory.objects.create(
                day=self,
                name=prev_category.name,
                score=None,
                max_score=None
            )
            
            # Copy targets from previous category
            prev_targets = prev_category.targets.filter(is_deleted=False)
            for prev_target in prev_targets:
                Target.objects.create(
                    name=prev_target.name,
                    category=new_category,
                    importance=prev_target.importance,
                    is_achieved=False  # Reset achievement status
                )

    @classmethod
    def get_or_create_today(cls):
        """Get or create ScoreDay for today"""
        today = timezone.now().date()
        score_day, created = cls.objects.get_or_create(
            day=today,
            defaults={'score': None, 'max_score': None}
        )
        
        if created:
            score_day.copy_previous_day_categories()
            score_day.calculate_scores()
        
        return score_day


class TargetCategory(BaseModel):
    day = models.ForeignKey(ScoreDay, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=200)
    score = models.PositiveIntegerField(null=True, blank=True)
    max_score = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['day', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.day.day})"

    def calculate_scores(self):
        """Calculate category scores from targets"""
        targets = self.targets.filter(is_deleted=False)
        
        # Calculate max score: number of targets × highest importance score
        target_count = targets.count()
        max_importance_score = Importance.get_max_score()
        self.max_score = target_count * max_importance_score
        
        # Calculate actual score: sum of achieved targets' importance scores
        achieved_targets = targets.filter(is_achieved=True)
        self.score = sum(target.importance.score for target in achieved_targets)
        
        # Save without triggering signals to prevent recursion
        self.save(update_fields=['score', 'max_score', 'updated_at'])

    def get_normalized_score(self):
        """Return display-friendly normalized score"""
        if not self.max_score or self.max_score == 0:
            return 0
        
        percentage = (self.score / self.max_score) * 100
        
        # Determine normalization factor based on score magnitude
        if self.max_score >= 100:
            factor = 100
        else:
            factor = 10
            
        return round(percentage * factor / 100, 1)


class Target(BaseModel):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(TargetCategory, on_delete=models.CASCADE, related_name='targets')
    importance = models.ForeignKey(Importance, on_delete=models.CASCADE)
    is_achieved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-importance__score', 'name']

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    def toggle_achievement(self):
        """Toggle achievement status and trigger recalculation"""
        self.is_achieved = not self.is_achieved
        self.save()
        
        # Trigger recalculation of category and day scores
        self.category.calculate_scores()
        self.category.day.calculate_scores()


# Signal handlers for automatic recalculation

@receiver(post_save, sender=Target)
def target_post_save_handler(sender, instance, created, **kwargs):
    """
    Signal handler for Target model post_save.
    Triggers score recalculation when targets are created or updated.
    Requirements: 8.1, 8.2
    """
    # Only recalculate if the target is not deleted
    if not instance.is_deleted:
        # Recalculate category scores
        instance.category.calculate_scores()
        # Recalculate day scores
        instance.category.day.calculate_scores()


@receiver(post_delete, sender=Target)
def target_post_delete_handler(sender, instance, **kwargs):
    """
    Signal handler for Target model post_delete.
    Triggers score recalculation when targets are deleted.
    Requirements: 8.1, 8.2
    """
    # Recalculate category and day scores after target deletion
    if instance.category_id:
        try:
            category = TargetCategory.objects.get(id=instance.category_id)
            category.calculate_scores()
            category.day.calculate_scores()
        except TargetCategory.DoesNotExist:
            pass


@receiver(post_save, sender=Importance)
def importance_post_save_handler(sender, instance, created, **kwargs):
    """
    Signal handler for Importance model post_save.
    Triggers global recalculation when importance levels are modified.
    Requirements: 3.5, 8.1, 8.3
    """
    # Recalculate all scores across all days when importance levels change
    for score_day in ScoreDay.objects.filter(is_deleted=False):
        score_day.calculate_scores()


@receiver(post_delete, sender=Importance)
def importance_post_delete_handler(sender, instance, **kwargs):
    """
    Signal handler for Importance model post_delete.
    Triggers global recalculation when importance levels are deleted.
    Requirements: 3.5, 8.1, 8.3
    """
    # Recalculate all scores across all days when importance levels are deleted
    for score_day in ScoreDay.objects.filter(is_deleted=False):
        score_day.calculate_scores()


@receiver(post_save, sender=TargetCategory)
def target_category_post_save_handler(sender, instance, created, **kwargs):
    """
    Signal handler for TargetCategory model post_save.
    Triggers day score recalculation when categories are modified.
    Requirements: 8.2, 8.3
    """
    # Only recalculate if the category is not deleted and this isn't a score update
    update_fields = kwargs.get('update_fields')
    if not instance.is_deleted and not update_fields:
        # Recalculate day scores when category is modified
        instance.day.calculate_scores()
    elif instance.is_deleted:
        # If category is being marked as deleted, recalculate to exclude it
        instance.day.calculate_scores()


@receiver(post_delete, sender=TargetCategory)
def target_category_post_delete_handler(sender, instance, **kwargs):
    """
    Signal handler for TargetCategory model post_delete.
    Triggers day score recalculation when categories are deleted.
    Requirements: 8.2, 8.3
    """
    # Recalculate day scores after category deletion
    if instance.day_id:
        try:
            day = ScoreDay.objects.get(id=instance.day_id)
            day.calculate_scores()
        except ScoreDay.DoesNotExist:
            pass
