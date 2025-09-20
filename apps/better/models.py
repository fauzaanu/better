from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.shortcuts import get_object_or_404


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

    @classmethod
    def get_management_context(cls):
        """Get context data for importance management page"""
        from .forms import ImportanceForm
        
        importance_levels = cls.objects.all().order_by('-score')
        create_form = ImportanceForm()
        
        return {
            'importance_levels': importance_levels,
            'create_form': create_form,
            'page_title': 'Manage Importance Levels',
            'has_importance_levels': importance_levels.exists(),
        }

    @classmethod
    def create_from_form(cls, form_data):
        """Create new importance level from form data"""
        from .forms import ImportanceForm
        
        form = ImportanceForm(form_data)
        
        if form.is_valid():
            importance = form.save()
            success_message = (
                f'Importance level "{importance.label}" with score {importance.score} '
                f'has been created successfully. All scores have been recalculated automatically.'
            )
            return importance, success_message, None
        
        # Form has errors - return context for re-rendering
        importance_levels = cls.objects.all().order_by('-score')
        context = {
            'importance_levels': importance_levels,
            'create_form': form,  # Form with errors
            'page_title': 'Manage Importance Levels',
            'has_importance_levels': importance_levels.exists(),
            'form_errors': True,
        }
        return None, None, context

    def update_from_form(self, form_data):
        """Update importance level from form data"""
        from .forms import ImportanceForm
        
        original_score = self.score
        form = ImportanceForm(form_data, instance=self)
        
        if form.is_valid():
            updated_importance = form.save()
            
            # Generate appropriate success message
            if original_score != updated_importance.score:
                success_message = (
                    f'Importance level "{updated_importance.label}" has been updated successfully. '
                    f'Score changed from {original_score} to {updated_importance.score}. '
                    f'All scores have been recalculated automatically.'
                )
            else:
                success_message = (
                    f'Importance level "{updated_importance.label}" has been updated successfully.'
                )
            
            return updated_importance, success_message, None
        
        # Form has validation errors
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f'{field.title()}: {error}')
        
        return None, None, error_messages

    def can_be_deleted(self):
        """Check if importance level can be safely deleted"""
        targets_count = Target.objects.filter(
            importance=self,
            is_deleted=False
        ).count()
        
        if targets_count > 0:
            error_message = (
                f'Cannot delete importance level "{self.label}" because it is being used by '
                f'{targets_count} target(s). Please reassign or delete those targets first.'
            )
            return False, error_message
        
        return True, None

    def delete_with_message(self):
        """Delete importance level and return success message"""
        can_delete, error_message = self.can_be_deleted()
        
        if not can_delete:
            return False, error_message
        
        label = self.label
        score = self.score
        self.delete()
        
        success_message = (
            f'Importance level "{label}" (score: {score}) has been deleted successfully. '
            f'All scores have been recalculated automatically.'
        )
        
        return True, success_message

    @classmethod
    def handle_management_action(cls, action, form_data):
        """Handle CRUD operations for importance management"""
        if action == 'create':
            return cls._handle_create_action(form_data)
        elif action == 'update':
            return cls._handle_update_action(form_data)
        elif action == 'delete':
            return cls._handle_delete_action(form_data)
        else:
            return 'error', 'Invalid action specified.', None

    @classmethod
    def _handle_create_action(cls, form_data):
        """Handle create action"""
        importance, success_message, error_context = cls.create_from_form(form_data)
        
        if importance:
            return 'success', success_message, None
        else:
            return 'render', None, error_context

    @classmethod
    def _handle_update_action(cls, form_data):
        """Handle update action"""
        importance_id = form_data.get('importance_id')
        
        if not importance_id:
            return 'error', 'No importance level specified for update.', None
        
        try:
            importance = get_object_or_404(cls, id=importance_id)
            updated_importance, success_message, error_messages = importance.update_from_form(form_data)
            
            if updated_importance:
                return 'success', success_message, None
            else:
                # Join error messages
                error_message = '; '.join(error_messages) if error_messages else 'Validation failed.'
                return 'error', error_message, None
                
        except cls.DoesNotExist:
            return 'error', 'Importance level not found.', None
        except Exception:
            return 'error', 'An error occurred while updating the importance level.', None

    @classmethod
    def _handle_delete_action(cls, form_data):
        """Handle delete action"""
        importance_id = form_data.get('importance_id')
        
        if not importance_id:
            return 'error', 'No importance level specified for deletion.', None
        
        try:
            importance = get_object_or_404(cls, id=importance_id)
            success, message = importance.delete_with_message()
            
            if success:
                return 'success', message, None
            else:
                return 'error', message, None
                
        except cls.DoesNotExist:
            return 'error', 'Importance level not found.', None
        except Exception:
            return 'error', 'An error occurred while deleting the importance level.', None


class ScoreDay(BaseModel):
    day = models.DateField(unique=True)
    score = models.PositiveIntegerField(null=True, blank=True)
    max_score = models.PositiveIntegerField(null=True, blank=True)
    wake_time = models.DateTimeField(null=True, blank=True, help_text="Time when you woke up")
    sleep_time = models.DateTimeField(null=True, blank=True, help_text="Time when you went to sleep")

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

    def get_display_score(self, baseline=10):
        """Return score multiplied by baseline for display purposes"""
        if not self.max_score or self.max_score == 0:
            return 0
        
        percentage = (self.score / self.max_score)
        return round(percentage * baseline, 1)

    def get_score_color_class(self):
        """Return Tailwind color class based on score percentage"""
        if not self.max_score or self.max_score == 0:
            return "text-zinc-500"
        
        percentage = (self.score / self.max_score) * 100
        
        if percentage >= 90:
            return "text-green-400"
        elif percentage >= 75:
            return "text-green-500"
        elif percentage >= 60:
            return "text-yellow-400"
        elif percentage >= 40:
            return "text-orange-400"
        elif percentage >= 20:
            return "text-red-400"
        else:
            return "text-red-500"

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
                description=prev_category.description,
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

    def get_yesterday_change(self):
        """Calculate percentage change compared to yesterday"""
        from datetime import timedelta
        
        yesterday_date = self.day - timedelta(days=1)
        try:
            yesterday = ScoreDay.objects.get(day=yesterday_date, is_deleted=False)
            
            # Calculate percentage change
            if yesterday.max_score and yesterday.max_score > 0 and self.max_score and self.max_score > 0:
                yesterday_percentage = (yesterday.score / yesterday.max_score) * 100
                today_percentage = (self.score / self.max_score) * 100
                return today_percentage - yesterday_percentage
            
        except ScoreDay.DoesNotExist:
            pass
        
        return None

    def get_active_hours(self):
        """Calculate active hours between wake and sleep time"""
        if not self.wake_time:
            return None
        
        if self.sleep_time:
            # Calculate duration between wake and sleep
            duration = self.sleep_time - self.wake_time
            return round(duration.total_seconds() / 3600, 1)  # Convert to hours
        
        # If no sleep time yet, calculate from wake time to now (for current day)
        if self.day == timezone.now().date():
            now = timezone.now()
            duration = now - self.wake_time
            return round(duration.total_seconds() / 3600, 1)
        
        return None

    def has_wake_time(self):
        """Check if wake time is set"""
        return self.wake_time is not None

    def get_previous_day(self):
        """Get the previous ScoreDay if it exists"""
        from datetime import timedelta
        previous_date = self.day - timedelta(days=1)
        return ScoreDay.objects.filter(
            day=previous_date,
            is_deleted=False
        ).first()
    
    def get_next_day(self):
        """Get the next ScoreDay if it exists and is not in the future"""
        from datetime import timedelta
        next_date = self.day + timedelta(days=1)
        
        # Don't allow navigation to future days
        if next_date > timezone.now().date():
            return None
            
        return ScoreDay.objects.filter(
            day=next_date,
            is_deleted=False
        ).first()

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

    def get_dashboard_context(self, sleep_wake_form=None):
        """Get comprehensive dashboard context data."""
        from .forms import SleepWakeTimeForm
        
        if sleep_wake_form is None:
            sleep_wake_form = SleepWakeTimeForm(instance=self)
        
        # Get yesterday's data
        yesterday_day = self.get_previous_day()
        
        # Get categories with optimized queries
        categories = self.categories.filter(is_deleted=False).prefetch_related(
            'targets__importance'
        ).order_by('name')
        
        # Prepare categories data
        categories_data = []
        for category in categories:
            targets = category.targets.filter(is_deleted=False).order_by('-importance__score', 'name')
            category.yesterday_change = category.get_yesterday_change()
            categories_data.append({
                'category': category,
                'targets': targets,
                'achieved_count': targets.filter(is_achieved=True).count(),
                'total_count': targets.count(),
                'normalized_score': category.get_normalized_score()
            })
        
        # Prepare yesterday's categories data
        yesterday_categories = []
        if yesterday_day:
            for category in yesterday_day.categories.filter(is_deleted=False).order_by('name'):
                yesterday_categories.append({
                    'category': category,
                    'targets': category.targets.filter(is_deleted=False),
                    'achieved_count': category.targets.filter(is_deleted=False, is_achieved=True).count(),
                    'total_count': category.targets.filter(is_deleted=False).count(),
                })
        
        # Calculate progress percentage
        progress_percentage = 0
        if self.max_score and self.max_score > 0:
            progress_percentage = round((self.score / self.max_score) * 100, 1)
        
        self.yesterday_change = self.get_yesterday_change()
        
        return {
            'current_day': self,
            'yesterday_day': yesterday_day,
            'categories_data': categories_data,
            'yesterday_categories': yesterday_categories,
            'progress_percentage': progress_percentage,
            'normalized_daily_score': self.get_normalized_score(),
            'importance_levels': Importance.objects.all().order_by('-score'),
            'has_categories': categories.exists(),
            'has_importance_levels': Importance.objects.exists(),
            'sleep_wake_form': sleep_wake_form,
            'is_first_day': yesterday_day is None,
            'has_yesterday_data': yesterday_day is not None and yesterday_categories,
            'is_today': self.day == timezone.now().date(),
        }


class TargetCategory(BaseModel):
    day = models.ForeignKey(ScoreDay, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Description of what this category represents")
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

    def get_display_score(self, baseline=10):
        """Return score multiplied by baseline for display purposes"""
        if not self.max_score or self.max_score == 0:
            return 0
        
        percentage = (self.score / self.max_score)
        return round(percentage * baseline, 1)

    def get_score_color_class(self):
        """Return Tailwind color class based on score percentage"""
        if not self.max_score or self.max_score == 0:
            return "text-zinc-500"
        
        percentage = (self.score / self.max_score) * 100
        
        if percentage >= 90:
            return "text-green-400"
        elif percentage >= 75:
            return "text-green-500"
        elif percentage >= 60:
            return "text-yellow-400"
        elif percentage >= 40:
            return "text-orange-400"
        elif percentage >= 20:
            return "text-red-400"
        else:
            return "text-red-500"

    def get_yesterday_change(self):
        """Calculate percentage change compared to yesterday's same category"""
        from datetime import timedelta
        
        yesterday_date = self.day.day - timedelta(days=1)
        try:
            yesterday_day = ScoreDay.objects.get(day=yesterday_date, is_deleted=False)
            yesterday_category = yesterday_day.categories.get(name=self.name, is_deleted=False)
            
            # Calculate percentage change
            if (yesterday_category.max_score and yesterday_category.max_score > 0 and 
                self.max_score and self.max_score > 0):
                yesterday_percentage = (yesterday_category.score / yesterday_category.max_score) * 100
                today_percentage = (self.score / self.max_score) * 100
                return today_percentage - yesterday_percentage
            
        except (ScoreDay.DoesNotExist, TargetCategory.DoesNotExist):
            pass
        
        return None

    @classmethod
    def get_for_today(cls, pk):
        """Get category for today with proper validation"""
        current_day = ScoreDay.get_or_create_today()
        return get_object_or_404(
            cls,
            pk=pk,
            day=current_day,
            is_deleted=False
        )

    def get_update_context(self):
        """Get context data for category update form"""
        from .forms import TargetCategoryForm
        
        form = TargetCategoryForm(instance=self, current_day=self.day)
        
        return {
            'form': form,
            'object': self,
            'page_title': f'Update Category: {self.name}',
            'submit_text': 'Update Category',
            'is_update': True
        }

    def update_from_form(self, form_data):
        """Update category from form data"""
        from .forms import TargetCategoryForm
        
        form = TargetCategoryForm(form_data, instance=self, current_day=self.day)
        
        if form.is_valid():
            updated_category = form.save()
            success_message = f'Category "{updated_category.name}" has been updated successfully.'
            return updated_category, success_message, None
        
        # Form has errors - return context for re-rendering
        context = {
            'form': form,
            'object': self,
            'page_title': f'Update Category: {self.name}',
            'submit_text': 'Update Category',
            'is_update': True
        }
        return None, None, context

    def get_delete_context(self):
        """Get context data for category deletion confirmation"""
        target_count = self.targets.filter(is_deleted=False).count()
        
        return {
            'object': self,
            'page_title': f'Delete Category: {self.name}',
            'target_count': target_count,
            'category_name': self.name
        }

    def soft_delete_with_targets(self):
        """Soft delete category and all its targets"""
        category_name = self.name
        
        # Soft delete the category
        self.is_deleted = True
        self.save()
        
        # Soft delete all associated targets
        self.targets.filter(is_deleted=False).update(is_deleted=True)
        
        # Recalculate scores after deletion
        self.day.calculate_scores()
        
        success_message = f'Category "{category_name}" and all its targets have been removed successfully.'
        return success_message


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

    def get_achievement_message(self):
        """Get success message for achievement toggle"""
        action = "completed" if self.is_achieved else "marked as incomplete"
        return f'Target "{self.name}" has been {action}.'

    @classmethod
    def get_target_for_achievement(cls, pk, current_day):
        """Get target for achievement toggle with proper validation"""
        return get_object_or_404(
            cls,
            pk=pk,
            category__day=current_day,
            is_deleted=False
        )

    @classmethod
    def get_create_context(cls, current_day, category_id=None):
        """Get context data for target creation form"""
        from .forms import TargetForm
        
        # Handle initial category selection
        initial = {}
        if category_id:
            try:
                category = TargetCategory.objects.get(
                    id=category_id,
                    day=current_day,
                    is_deleted=False
                )
                initial['category'] = category
            except TargetCategory.DoesNotExist:
                pass  # Invalid category ID, ignore
        
        form = TargetForm(initial=initial, current_day=current_day)
        
        return {
            'form': form,
            'page_title': 'Create New Target',
            'submit_text': 'Create Target',
            'current_day': current_day,
            'categories_count': current_day.categories.filter(is_deleted=False).count(),
            'importance_levels': Importance.objects.all().order_by('-score')
        }

    @classmethod
    def create_from_form(cls, form_data, current_day):
        """Create a new target from form data"""
        from .forms import TargetForm
        
        form = TargetForm(form_data, current_day=current_day)
        
        if form.is_valid():
            target = form.save(commit=False)
            target.is_achieved = False  # Initialize as not achieved
            target.save()
            return target, None  # target, error
        
        return None, form  # target, error_form


