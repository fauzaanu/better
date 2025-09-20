from django import forms
from django.core.exceptions import ValidationError
from .models import TargetCategory, Target, Importance


class TargetCategoryForm(forms.ModelForm):
    """
    Form for creating and updating target categories.
    Requirements: 6.3, 6.4
    """
    
    class Meta:
        model = TargetCategory
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name',
                'maxlength': 200
            })
        }
    
    def __init__(self, current_day=None, *args, **kwargs):
        self.current_day = current_day
        super().__init__(*args, **kwargs)
        
        # Add required attribute to name field
        self.fields['name'].required = True
        self.fields['name'].help_text = 'Category name must be unique for the current day'
    
    def clean_name(self):
        """
        Validate that category name is unique for the current day.
        Requirements: 6.3, 6.4
        """
        name = self.cleaned_data.get('name')
        
        if not name:
            raise ValidationError('Category name is required.')
        
        # Strip whitespace and validate length
        name = name.strip()
        if len(name) < 1:
            raise ValidationError('Category name cannot be empty.')
        
        if len(name) > 200:
            raise ValidationError('Category name cannot exceed 200 characters.')
        
        # Check uniqueness for current day (excluding current instance if updating)
        if self.current_day:
            existing_categories = TargetCategory.objects.filter(
                day=self.current_day,
                name__iexact=name,
                is_deleted=False
            )
            
            # If updating, exclude current instance
            if self.instance and self.instance.pk:
                existing_categories = existing_categories.exclude(pk=self.instance.pk)
            
            if existing_categories.exists():
                raise ValidationError(f'A category with the name "{name}" already exists for this day.')
        
        return name


class TargetForm(forms.ModelForm):
    """
    Form for creating and updating targets with dynamic category filtering.
    Requirements: 6.2, 6.6
    """
    
    class Meta:
        model = Target
        fields = ['name', 'category', 'importance']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter target name',
                'maxlength': 200
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'importance': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, current_day=None, *args, **kwargs):
        self.current_day = current_day
        super().__init__(*args, **kwargs)
        
        # Filter categories to current day only
        if self.current_day:
            self.fields['category'].queryset = TargetCategory.objects.filter(
                day=self.current_day,
                is_deleted=False
            ).order_by('name')
        else:
            # If no current day provided, show empty queryset
            self.fields['category'].queryset = TargetCategory.objects.none()
        
        # Set importance queryset to all available importance levels
        self.fields['importance'].queryset = Importance.objects.all().order_by('-score')
        
        # Add required attributes and help text
        self.fields['name'].required = True
        self.fields['category'].required = True
        self.fields['importance'].required = True
        
        self.fields['name'].help_text = 'Descriptive name for your target'
        self.fields['category'].help_text = 'Select the category this target belongs to'
        self.fields['importance'].help_text = 'Choose the importance level for this target'
        
        # Add empty labels for better UX
        self.fields['category'].empty_label = "Select a category"
        self.fields['importance'].empty_label = "Select importance level"
    
    def clean_name(self):
        """
        Validate target name.
        Requirements: 6.2, 6.6
        """
        name = self.cleaned_data.get('name')
        
        if not name:
            raise ValidationError('Target name is required.')
        
        # Strip whitespace and validate length
        name = name.strip()
        if len(name) < 1:
            raise ValidationError('Target name cannot be empty.')
        
        if len(name) > 200:
            raise ValidationError('Target name cannot exceed 200 characters.')
        
        return name
    
    def clean_category(self):
        """
        Validate that selected category belongs to current day.
        Requirements: 6.2, 6.6
        """
        category = self.cleaned_data.get('category')
        
        if not category:
            raise ValidationError('Please select a category.')
        
        # Ensure category belongs to current day and is not deleted
        if self.current_day and category.day != self.current_day:
            raise ValidationError('Selected category does not belong to the current day.')
        
        if category.is_deleted:
            raise ValidationError('Selected category is no longer available.')
        
        return category
    
    def clean_importance(self):
        """
        Validate importance selection.
        Requirements: 6.2, 6.6
        """
        importance = self.cleaned_data.get('importance')
        
        if not importance:
            raise ValidationError('Please select an importance level.')
        
        return importance


class ImportanceForm(forms.ModelForm):
    """
    Form for creating and updating importance levels.
    Requirements: 6.7
    """
    
    class Meta:
        model = Importance
        fields = ['label', 'score']
        widgets = {
            'label': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter importance label (e.g., Critical, Important)',
                'maxlength': 200
            }),
            'score': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter numeric score (1 or higher)',
                'min': 1
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add required attributes and help text
        self.fields['label'].required = True
        self.fields['score'].required = True
        
        self.fields['label'].help_text = 'Descriptive label for this importance level'
        self.fields['score'].help_text = 'Numeric score (higher numbers = more important)'
    
    def clean_label(self):
        """
        Validate importance label uniqueness.
        Requirements: 6.7
        """
        label = self.cleaned_data.get('label')
        
        if not label:
            raise ValidationError('Importance label is required.')
        
        # Strip whitespace and validate length
        label = label.strip()
        if len(label) < 1:
            raise ValidationError('Importance label cannot be empty.')
        
        if len(label) > 200:
            raise ValidationError('Importance label cannot exceed 200 characters.')
        
        # Check uniqueness (case-insensitive)
        existing_importance = Importance.objects.filter(label__iexact=label)
        
        # If updating, exclude current instance
        if self.instance and self.instance.pk:
            existing_importance = existing_importance.exclude(pk=self.instance.pk)
        
        if existing_importance.exists():
            raise ValidationError(f'An importance level with the label "{label}" already exists.')
        
        return label
    
    def clean_score(self):
        """
        Validate importance score.
        Requirements: 6.7
        """
        score = self.cleaned_data.get('score')
        
        if score is None:
            raise ValidationError('Importance score is required.')
        
        if score < 1:
            raise ValidationError('Importance score must be 1 or higher.')
        
        if score > 999999:  # Reasonable upper limit
            raise ValidationError('Importance score is too large.')
        
        return score


class TargetAchievementForm(forms.Form):
    """
    Simple form for toggling target achievement status.
    Requirements: 6.2
    """
    
    target_id = forms.IntegerField(widget=forms.HiddenInput())
    
    def __init__(self, target=None, *args, **kwargs):
        self.target = target
        super().__init__(*args, **kwargs)
        
        if self.target:
            self.fields['target_id'].initial = self.target.id
    
    def clean_target_id(self):
        """
        Validate that target exists and is not deleted.
        Requirements: 6.2
        """
        target_id = self.cleaned_data.get('target_id')
        
        if not target_id:
            raise ValidationError('Target ID is required.')
        
        try:
            target = Target.objects.get(id=target_id, is_deleted=False)
        except Target.DoesNotExist:
            raise ValidationError('Target not found or no longer available.')
        
        return target_id


class SleepWakeTimeForm(forms.Form):
    """
    Form for updating sleep and wake times for a ScoreDay.
    Uses time fields and combines with the day's date.
    """
    
    wake_time = forms.TimeField(required=True)
    sleep_time = forms.TimeField(required=False)
    
    def __init__(self, instance=None, *args, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        wake_time = cleaned_data.get('wake_time')
        sleep_time = cleaned_data.get('sleep_time')
        
        if wake_time and sleep_time:
            if sleep_time <= wake_time:
                raise ValidationError('Sleep time must be after wake time.')
        
        return cleaned_data
    
    def save(self):
        """Save the time data to the ScoreDay instance"""
        if not self.instance:
            raise ValueError('No ScoreDay instance provided')
        
        from django.utils import timezone
        from datetime import datetime
        
        wake_time = self.cleaned_data.get('wake_time')
        sleep_time = self.cleaned_data.get('sleep_time')
        
        # Combine date with time to create datetime objects
        day_date = self.instance.day
        
        if wake_time:
            wake_datetime = timezone.make_aware(
                datetime.combine(day_date, wake_time)
            )
            self.instance.wake_time = wake_datetime
        
        if sleep_time:
            # Sleep time could be next day if it's earlier than wake time
            sleep_datetime = timezone.make_aware(
                datetime.combine(day_date, sleep_time)
            )
            
            # If sleep time is before wake time, assume it's next day
            if wake_time and sleep_time < wake_time:
                from datetime import timedelta
                sleep_datetime += timedelta(days=1)
            
            self.instance.sleep_time = sleep_datetime
        elif 'sleep_time' in self.cleaned_data:
            # If sleep_time field was submitted but empty, clear it
            self.instance.sleep_time = None
        
        self.instance.save()
        return self.instance