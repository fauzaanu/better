from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from datetime import timedelta
from .models import ScoreDay, TargetCategory, Target, Importance
from .forms import TargetCategoryForm, TargetForm, TargetAchievementForm, ImportanceForm, SleepWakeTimeForm


class DashboardView(View):
    """
    Dashboard view for displaying current day's scores and targets with three-panel layout.
    Requirements: 1.3, 1.5, 5.2, 5.4, 5.5, 6.1, 1.1, 1.4, 8.4
    """
    
    def get(self, request):
        """
        Handle GET requests to display dashboard with three-panel layout data.
        
        - Retrieves or creates current day's ScoreDay (handles first-time usage)
        - Retrieves yesterday's ScoreDay for left panel comparison
        - Prepares context data for all three panels (left, center, right)
        - Handles edge cases for first day usage when no yesterday data exists
        - Ensures all data needed for real-time updates is included
        """
        # Get or create today's ScoreDay (handles first-time usage - Requirement 5.5)
        current_day = ScoreDay.get_or_create_today()
        
        # Create sleep/wake time form for current day
        sleep_wake_form = SleepWakeTimeForm(instance=current_day)
        
        # Get yesterday's ScoreDay for left panel (Requirements 1.3, 5.2, 5.4)
        yesterday_day = ScoreDay.objects.filter(
            day=current_day.day - timedelta(days=1)
        ).first()
        
        # Get all categories for the current day with their targets (optimized queries)
        categories = current_day.categories.filter(is_deleted=False).prefetch_related(
            'targets__importance'
        ).order_by('name')
        
        # Prepare categories data for center and right panels (Requirements 1.5, 5.2)
        categories_data = []
        for category in categories:
            targets = category.targets.filter(is_deleted=False).order_by('-importance__score', 'name')
            # Add yesterday change to category object for template access
            category.yesterday_change = category.get_yesterday_change()
            categories_data.append({
                'category': category,
                'targets': targets,
                'achieved_count': targets.filter(is_achieved=True).count(),
                'total_count': targets.count(),
                'normalized_score': category.get_normalized_score()
            })
        
        # Prepare yesterday's categories data for left panel (Requirements 5.2, 5.4, 5.5)
        yesterday_categories = []
        if yesterday_day:
            # Get yesterday's categories with their final scores
            for category in yesterday_day.categories.filter(is_deleted=False).order_by('name'):
                yesterday_categories.append({
                    'category': category,
                    'targets': category.targets.filter(is_deleted=False),
                    'achieved_count': category.targets.filter(is_deleted=False, is_achieved=True).count(),
                    'total_count': category.targets.filter(is_deleted=False).count(),
                })
        
        # Get available importance levels for context
        importance_levels = Importance.objects.all().order_by('-score')
        
        # Calculate overall progress percentage for right panel (Requirement 1.5)
        progress_percentage = 0
        if current_day.max_score and current_day.max_score > 0:
            progress_percentage = round((current_day.score / current_day.max_score) * 100, 1)
        
        # Add yesterday change to current day for template access
        current_day.yesterday_change = current_day.get_yesterday_change()
        
        # Prepare comprehensive context for three-panel layout
        context = {
            # Core day data
            'current_day': current_day,
            'yesterday_day': yesterday_day,
            
            # Panel-specific data
            'categories_data': categories_data,  # Center and right panels
            'yesterday_categories': yesterday_categories,  # Left panel
            
            # Progress and scoring data
            'progress_percentage': progress_percentage,
            'normalized_daily_score': current_day.get_normalized_score(),
            
            # Additional context for forms and UI
            'importance_levels': importance_levels,
            'has_categories': categories.exists(),
            'has_importance_levels': importance_levels.exists(),
            'sleep_wake_form': sleep_wake_form,
            
            # Edge case handling flags
            'is_first_day': yesterday_day is None,  # For first-time usage messaging
            'has_yesterday_data': yesterday_day is not None and yesterday_categories,
            'is_today': True,  # Dashboard always shows today
        }
        
        return render(request, "better/dashboard.html", context)
    
    def post(self, request):
        """Handle POST requests for updating sleep/wake times"""
        current_day = ScoreDay.get_or_create_today()
        sleep_wake_form = SleepWakeTimeForm(data=request.POST, instance=current_day)
        
        if sleep_wake_form.is_valid():
            sleep_wake_form.save()
            messages.success(request, 'Sleep/wake times updated successfully.')
            return redirect('better:dashboard')
        else:
            # Re-render with form errors
            # Get all the same context data as GET request
            yesterday_day = ScoreDay.objects.filter(
                day=current_day.day - timedelta(days=1)
            ).first()
            
            categories = current_day.categories.filter(is_deleted=False).prefetch_related(
                'targets__importance'
            ).order_by('name')
            
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
            
            yesterday_categories = []
            if yesterday_day:
                for category in yesterday_day.categories.filter(is_deleted=False).order_by('name'):
                    yesterday_categories.append({
                        'category': category,
                        'targets': category.targets.filter(is_deleted=False),
                        'achieved_count': category.targets.filter(is_deleted=False, is_achieved=True).count(),
                        'total_count': category.targets.filter(is_deleted=False).count(),
                    })
            
            importance_levels = Importance.objects.all().order_by('-score')
            progress_percentage = 0
            if current_day.max_score and current_day.max_score > 0:
                progress_percentage = round((current_day.score / current_day.max_score) * 100, 1)
            
            current_day.yesterday_change = current_day.get_yesterday_change()
            
            context = {
                'current_day': current_day,
                'yesterday_day': yesterday_day,
                'categories_data': categories_data,
                'yesterday_categories': yesterday_categories,
                'progress_percentage': progress_percentage,
                'normalized_daily_score': current_day.get_normalized_score(),
                'importance_levels': importance_levels,
                'has_categories': categories.exists(),
                'has_importance_levels': importance_levels.exists(),
                'sleep_wake_form': sleep_wake_form,  # Form with errors
                'is_first_day': yesterday_day is None,
                'has_yesterday_data': yesterday_day is not None and yesterday_categories,
            }
            
            return render(request, "better/dashboard.html", context)


class TargetCategoryCreateView(CreateView):
    """
    View for creating new target categories for the current day.
    Requirements: 6.3, 2.2
    """
    model = TargetCategory
    form_class = TargetCategoryForm
    template_name = 'better/category_form.html'
    success_url = reverse_lazy('better:dashboard')
    
    def get_form_kwargs(self):
        """Pass current day to form for validation"""
        kwargs = super().get_form_kwargs()
        kwargs['current_day'] = ScoreDay.get_or_create_today()
        return kwargs
    
    def form_valid(self, form):
        """Set the day to current day before saving"""
        current_day = ScoreDay.get_or_create_today()
        form.instance.day = current_day
        
        # Initialize scores as null (will be calculated by signals)
        form.instance.score = None
        form.instance.max_score = None
        
        response = super().form_valid(form)
        
        messages.success(
            self.request, 
            f'Category "{form.instance.name}" has been created successfully.'
        )
        
        return response
    
    def get_context_data(self, **kwargs):
        """Add additional context for template"""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create New Category'
        context['submit_text'] = 'Create Category'
        return context


class TargetCategoryUpdateView(UpdateView):
    """
    View for updating existing target categories.
    Only affects current day's categories.
    Requirements: 6.4, 2.3
    """
    model = TargetCategory
    form_class = TargetCategoryForm
    template_name = 'better/category_form.html'
    success_url = reverse_lazy('better:dashboard')
    
    def get_queryset(self):
        """Ensure only current day's categories can be updated"""
        current_day = ScoreDay.get_or_create_today()
        return TargetCategory.objects.filter(
            day=current_day,
            is_deleted=False
        )
    
    def get_form_kwargs(self):
        """Pass current day to form for validation"""
        kwargs = super().get_form_kwargs()
        kwargs['current_day'] = self.object.day
        return kwargs
    
    def form_valid(self, form):
        """Handle successful form submission"""
        response = super().form_valid(form)
        
        messages.success(
            self.request, 
            f'Category "{form.instance.name}" has been updated successfully.'
        )
        
        return response
    
    def get_context_data(self, **kwargs):
        """Add additional context for template"""
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Update Category: {self.object.name}'
        context['submit_text'] = 'Update Category'
        context['is_update'] = True
        return context


class TargetCategoryDeleteView(DeleteView):
    """
    View for deleting target categories from the current day.
    Uses soft delete to maintain data integrity.
    Requirements: 6.5, 2.4
    """
    model = TargetCategory
    template_name = 'better/category_confirm_delete.html'
    success_url = reverse_lazy('better:dashboard')
    
    def get_queryset(self):
        """Ensure only current day's categories can be deleted"""
        current_day = ScoreDay.get_or_create_today()
        return TargetCategory.objects.filter(
            day=current_day,
            is_deleted=False
        )
    
    def delete(self, request, *args, **kwargs):
        """
        Perform soft delete instead of hard delete.
        Also soft delete all associated targets.
        """
        self.object = self.get_object()
        category_name = self.object.name
        
        # Soft delete the category
        self.object.is_deleted = True
        self.object.save()
        
        # Soft delete all associated targets
        self.object.targets.filter(is_deleted=False).update(is_deleted=True)
        
        # Recalculate scores after deletion
        self.object.day.calculate_scores()
        
        messages.success(
            request, 
            f'Category "{category_name}" and all its targets have been removed successfully.'
        )
        
        return redirect(self.success_url)
    
    def get_context_data(self, **kwargs):
        """Add additional context for template"""
        context = super().get_context_data(**kwargs)
        
        # Get count of targets that will be affected
        target_count = self.object.targets.filter(is_deleted=False).count()
        
        context['page_title'] = f'Delete Category: {self.object.name}'
        context['target_count'] = target_count
        context['category_name'] = self.object.name
        
        return context


class TargetCreateView(CreateView):
    """
    View for creating new targets within categories.
    Requirements: 6.2, 6.6, 4.2
    """
    model = Target
    form_class = TargetForm
    template_name = 'better/target_form.html'
    success_url = reverse_lazy('better:dashboard')
    
    def get_form_kwargs(self):
        """Pass current day to form for category filtering"""
        kwargs = super().get_form_kwargs()
        kwargs['current_day'] = ScoreDay.get_or_create_today()
        return kwargs
    
    def get_initial(self):
        """Pre-select category if provided in URL parameters"""
        initial = super().get_initial()
        category_id = self.request.GET.get('category')
        if category_id:
            try:
                current_day = ScoreDay.get_or_create_today()
                category = TargetCategory.objects.get(
                    id=category_id,
                    day=current_day,
                    is_deleted=False
                )
                initial['category'] = category
            except TargetCategory.DoesNotExist:
                pass  # Invalid category ID, ignore
        return initial
    
    def form_valid(self, form):
        """Set default values before saving"""
        # Initialize is_achieved as false (default)
        form.instance.is_achieved = False
        
        response = super().form_valid(form)
        
        messages.success(
            self.request, 
            f'Target "{form.instance.name}" has been created successfully in category "{form.instance.category.name}".'
        )
        
        return response
    
    def get_context_data(self, **kwargs):
        """Add additional context for template"""
        context = super().get_context_data(**kwargs)
        current_day = ScoreDay.get_or_create_today()
        
        context['page_title'] = 'Create New Target'
        context['submit_text'] = 'Create Target'
        context['current_day'] = current_day
        context['categories_count'] = current_day.categories.filter(is_deleted=False).count()
        context['importance_levels'] = Importance.objects.all().order_by('-score')
        
        return context


class TargetAchievementView(View):
    """
    View for toggling target achievement status.
    Handles POST requests to update target completion and trigger score recalculation.
    Supports HTMX requests by returning partial HTML templates.
    Requirements: 3.1, 3.2, 3.3, 3.4, 4.3
    """
    
    def post(self, request, pk):
        """
        Handle POST requests to toggle target achievement.
        
        - Validates target exists and belongs to current day
        - Toggles achievement status
        - Triggers automatic score recalculation via model method
        - Returns partial HTML templates for HTMX requests or redirects for form submissions
        """
        try:
            # Get target and ensure it belongs to current day and is not deleted
            current_day = ScoreDay.get_or_create_today()
            target = get_object_or_404(
                Target,
                pk=pk,
                category__day=current_day,
                is_deleted=False
            )
            
            # Store previous state for response message
            was_achieved = target.is_achieved
            
            # Toggle achievement status and trigger recalculation
            target.toggle_achievement()
            
            # Prepare success message
            action = "completed" if target.is_achieved else "marked as incomplete"
            message = f'Target "{target.name}" has been {action}.'
            
            # Handle HTMX requests - return partial HTML template
            if request.headers.get('HX-Request'):
                # Get updated context for today's scores
                context = self._get_scores_context(current_day)
                
                # Return multiple updates using HTMX response headers
                response = render(request, 'cotton/better/today-scores.html', context)
                
                # Add header to trigger target list update as well
                response['HX-Trigger-After-Swap'] = f'updateTarget-{target.id}'
                
                return response
            
            # Handle AJAX requests (legacy support)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'target_id': target.id,
                    'is_achieved': target.is_achieved,
                    'category_score': target.category.get_normalized_score(),
                    'daily_score': current_day.get_normalized_score(),
                })
            
            # Handle regular form submissions
            messages.success(request, message)
            return redirect('better:dashboard')
            
        except Target.DoesNotExist:
            error_message = 'Target not found or no longer available.'
            
            # Handle HTMX requests
            if request.headers.get('HX-Request'):
                return render(request, 'cotton/better/error-message.html', {
                    'error_message': error_message
                }, status=404)
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_message
                }, status=404)
            
            # Handle regular form submissions
            messages.error(request, error_message)
            return redirect('better:dashboard')
        
        except Exception as e:
            error_message = 'An error occurred while updating the target.'
            
            # Handle HTMX requests
            if request.headers.get('HX-Request'):
                return render(request, 'cotton/better/error-message.html', {
                    'error_message': error_message
                }, status=500)
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_message
                }, status=500)
            
            # Handle regular form submissions
            messages.error(request, error_message)
            return redirect('better:dashboard')
    
    def _get_scores_context(self, current_day):
        """
        Get context data for the today-scores component.
        Returns the same data structure as used in the dashboard for consistency.
        Requirements: 3.1, 3.2, 3.3, 3.4
        """
        # Get all categories for the current day with their targets (optimized queries)
        categories = current_day.categories.filter(is_deleted=False).prefetch_related(
            'targets__importance'
        ).order_by('name')
        
        # Prepare categories data with targets for template (same as dashboard)
        categories_data = []
        for category in categories:
            targets = category.targets.filter(is_deleted=False).order_by('-importance__score', 'name')
            # Add yesterday change to category object for template access
            category.yesterday_change = category.get_yesterday_change()
            categories_data.append({
                'category': category,
                'targets': targets,
                'achieved_count': targets.filter(is_achieved=True).count(),
                'total_count': targets.count(),
                'normalized_score': category.get_normalized_score()
            })
        
        # Calculate overall progress percentage (same calculation as dashboard)
        progress_percentage = 0
        if current_day.max_score and current_day.max_score > 0:
            progress_percentage = round((current_day.score / current_day.max_score) * 100, 1)
        
        # Add yesterday change to current day for template access
        current_day.yesterday_change = current_day.get_yesterday_change()
        
        return {
            'current_day': current_day,
            'categories_data': categories_data,
            'progress_percentage': progress_percentage,
            'normalized_daily_score': current_day.get_normalized_score(),
        }
    
    def get(self, request, pk):
        """
        Handle GET requests by redirecting to dashboard.
        Achievement toggling should only be done via POST for security.
        """
        messages.info(request, 'Target achievement can only be updated via form submission.')
        return redirect('better:dashboard')


class ImportanceManagementView(View):
    """
    View for managing importance levels with CRUD operations.
    Handles both GET requests to display current importance levels
    and POST requests for creating and updating importance levels.
    Requirements: 6.7, 3.1, 3.2, 3.3, 3.5
    """
    
    def get(self, request):
        """
        Handle GET requests to display current importance levels.
        
        - Retrieves all existing importance levels ordered by score (descending)
        - Prepares context data with importance levels and creation form
        - Returns context for template rendering
        """
        # Get all importance levels ordered by score (highest first)
        importance_levels = Importance.objects.all().order_by('-score')
        
        # Create form for adding new importance levels
        create_form = ImportanceForm()
        
        # Prepare context data
        context = {
            'importance_levels': importance_levels,
            'create_form': create_form,
            'page_title': 'Manage Importance Levels',
            'has_importance_levels': importance_levels.exists(),
        }
        
        return render(request, 'better/importance_management.html', context)
    
    def post(self, request):
        """
        Handle POST requests for creating and updating importance levels.
        
        - Processes form data for creating new importance levels
        - Validates form data and handles errors
        - Triggers global recalculation when importance scores change
        - Returns appropriate response based on success/failure
        """
        action = request.POST.get('action', 'create')
        
        if action == 'create':
            return self._handle_create(request)
        elif action == 'update':
            return self._handle_update(request)
        elif action == 'delete':
            return self._handle_delete(request)
        else:
            messages.error(request, 'Invalid action specified.')
            return redirect('better:importance-manage')
    
    def _handle_create(self, request):
        """
        Handle creation of new importance levels.
        Requirements: 6.7, 3.1, 3.2
        """
        form = ImportanceForm(request.POST)
        
        if form.is_valid():
            # Save the new importance level
            importance = form.save()
            
            messages.success(
                request,
                f'Importance level "{importance.label}" with score {importance.score} has been created successfully. '
                f'All scores have been recalculated automatically.'
            )
            
            # Note: Global recalculation is triggered automatically by the post_save signal
            # defined in models.py (importance_post_save_handler)
            
            return redirect('better:importance-manage')
        else:
            # Form has validation errors
            importance_levels = Importance.objects.all().order_by('-score')
            
            context = {
                'importance_levels': importance_levels,
                'create_form': form,  # Form with errors
                'page_title': 'Manage Importance Levels',
                'has_importance_levels': importance_levels.exists(),
                'form_errors': True,
            }
            
            return render(request, 'better/importance_management.html', context)
    
    def _handle_update(self, request):
        """
        Handle updating existing importance levels.
        Requirements: 6.7, 3.3, 3.5
        """
        importance_id = request.POST.get('importance_id')
        
        if not importance_id:
            messages.error(request, 'No importance level specified for update.')
            return redirect('better:importance-manage')
        
        try:
            importance = get_object_or_404(Importance, id=importance_id)
            original_label = importance.label
            original_score = importance.score
            
            form = ImportanceForm(request.POST, instance=importance)
            
            if form.is_valid():
                # Save the updated importance level
                updated_importance = form.save()
                
                # Check if score changed to provide appropriate message
                if original_score != updated_importance.score:
                    messages.success(
                        request,
                        f'Importance level "{updated_importance.label}" has been updated successfully. '
                        f'Score changed from {original_score} to {updated_importance.score}. '
                        f'All scores have been recalculated automatically.'
                    )
                else:
                    messages.success(
                        request,
                        f'Importance level "{updated_importance.label}" has been updated successfully.'
                    )
                
                # Note: Global recalculation is triggered automatically by the post_save signal
                # if the score changed
                
                return redirect('better:importance-manage')
            else:
                # Form has validation errors
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.title()}: {error}')
                
                return redirect('better:importance-manage')
                
        except Importance.DoesNotExist:
            messages.error(request, 'Importance level not found.')
            return redirect('better:importance-manage')
        except Exception as e:
            messages.error(request, 'An error occurred while updating the importance level.')
            return redirect('better:importance-manage')
    
    def _handle_delete(self, request):
        """
        Handle deletion of importance levels.
        Requirements: 6.7, 3.5
        """
        importance_id = request.POST.get('importance_id')
        
        if not importance_id:
            messages.error(request, 'No importance level specified for deletion.')
            return redirect('better:importance-manage')
        
        try:
            importance = get_object_or_404(Importance, id=importance_id)
            importance_label = importance.label
            importance_score = importance.score
            
            # Check if this importance level is being used by any targets
            targets_using_importance = Target.objects.filter(
                importance=importance,
                is_deleted=False
            ).count()
            
            if targets_using_importance > 0:
                messages.error(
                    request,
                    f'Cannot delete importance level "{importance_label}" because it is being used by '
                    f'{targets_using_importance} target(s). Please reassign or delete those targets first.'
                )
                return redirect('better:importance-manage')
            
            # Safe to delete
            importance.delete()
            
            messages.success(
                request,
                f'Importance level "{importance_label}" (score: {importance_score}) has been deleted successfully. '
                f'All scores have been recalculated automatically.'
            )
            
            # Note: Global recalculation is triggered automatically by the post_delete signal
            # defined in models.py (importance_post_delete_handler)
            
            return redirect('better:importance-manage')
            
        except Importance.DoesNotExist:
            messages.error(request, 'Importance level not found.')
            return redirect('better:importance-manage')
        except Exception as e:
            messages.error(request, 'An error occurred while deleting the importance level.')
            return redirect('better:importance-manage')


class DayView(View):
    """
    View for displaying a specific day's scores and targets.
    Allows viewing past days and updating sleep/wake times.
    """
    
    def get(self, request, pk):
        """Handle GET requests to display specific day's data"""
        # Get the ScoreDay by ID
        try:
            score_day = get_object_or_404(ScoreDay, pk=pk, is_deleted=False)
            target_date = score_day.day
        except ScoreDay.DoesNotExist:
            messages.error(request, 'Day not found.')
            return redirect('better:dashboard')
        
        # Create sleep/wake time form for this day
        sleep_wake_form = SleepWakeTimeForm(instance=score_day)
        
        # Get yesterday's ScoreDay for comparison
        yesterday_day = ScoreDay.objects.filter(
            day=target_date - timedelta(days=1),
            is_deleted=False
        ).first()
        
        # Get all categories for this day with their targets
        categories = score_day.categories.filter(is_deleted=False).prefetch_related(
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
        
        # Get available importance levels
        importance_levels = Importance.objects.all().order_by('-score')
        
        # Calculate progress percentage
        progress_percentage = 0
        if score_day.max_score and score_day.max_score > 0:
            progress_percentage = round((score_day.score / score_day.max_score) * 100, 1)
        
        score_day.yesterday_change = score_day.get_yesterday_change()
        
        # Check if this is today
        from django.utils import timezone
        is_today = target_date == timezone.now().date()
        
        context = {
            'current_day': score_day,
            'yesterday_day': yesterday_day,
            'categories_data': categories_data,
            'yesterday_categories': yesterday_categories,
            'progress_percentage': progress_percentage,
            'normalized_daily_score': score_day.get_normalized_score(),
            'importance_levels': importance_levels,
            'has_categories': categories.exists(),
            'has_importance_levels': importance_levels.exists(),
            'sleep_wake_form': sleep_wake_form,
            'is_first_day': yesterday_day is None,
            'has_yesterday_data': yesterday_day is not None and yesterday_categories,
            'is_today': is_today,
            'viewing_date': target_date,
        }
        
        return render(request, "better/dashboard.html", context)
    
    def post(self, request, pk):
        """Handle POST requests for updating sleep/wake times for specific day"""
        try:
            score_day = get_object_or_404(ScoreDay, pk=pk, is_deleted=False)
            target_date = score_day.day
        except ScoreDay.DoesNotExist:
            messages.error(request, 'Day not found.')
            return redirect('better:dashboard')
        
        sleep_wake_form = SleepWakeTimeForm(data=request.POST, instance=score_day)
        
        if sleep_wake_form.is_valid():
            sleep_wake_form.save()
            messages.success(request, f'Sleep/wake times updated for {target_date.strftime("%B %d, %Y")}.')
            return redirect('better:day-view', pk=pk)
        else:
            # Re-render with form errors - redirect to GET with error messages
            for field, errors in sleep_wake_form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.title()}: {error}')
            
            return redirect('better:day-view', pk=pk)

