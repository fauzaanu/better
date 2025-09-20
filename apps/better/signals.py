from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.better.models import TargetCategory, ScoreDay, Importance, Target


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
