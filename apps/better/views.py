from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from datetime import timedelta
from .models import ScoreDay, TargetCategory, Target, Importance
from .forms import TargetCategoryForm, TargetForm, ImportanceForm, SleepWakeTimeForm


class DashboardView(View):
    """Display today's dashboard with scores and targets."""
    
    def get(self, request):
        """Display dashboard with today's and yesterday's data."""
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
        """Update sleep and wake times."""
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


class TargetCategoryCreateView(View):
    """Create new target categories."""
    
    def get(self, request):
        """Show category creation form."""
        current_day = ScoreDay.get_or_create_today()
        form = TargetCategoryForm(current_day=current_day)
        
        context = {
            'form': form,
            'page_title': 'Create New Category',
            'submit_text': 'Create Category'
        }
        
        return render(request, 'better/category_form.html', context)
    
    def post(self, request):
        """Create new category."""
        current_day = ScoreDay.get_or_create_today()
        form = TargetCategoryForm(request.POST, current_day=current_day)
        
        if form.is_valid():
            # Set the day to current day before saving
            category = form.save(commit=False)
            category.day = current_day
            
            # Initialize scores as null (will be calculated by signals)
            category.score = None
            category.max_score = None
            category.save()
            
            messages.success(
                request, 
                f'Category "{category.name}" has been created successfully.'
            )
            
            return redirect('better:dashboard')
        
        # Form has errors, re-render with errors
        context = {
            'form': form,
            'page_title': 'Create New Category',
            'submit_text': 'Create Category'
        }
        
        return render(request, 'better/category_form.html', context)


class TargetCategoryUpdateView(View):
    """Update existing target categories."""
    
    def get_object(self, pk):
        """Get category for today."""
        current_day = ScoreDay.get_or_create_today()
        return get_object_or_404(
            TargetCategory,
            pk=pk,
            day=current_day,
            is_deleted=False
        )
    
    def get(self, request, pk):
        """Show category update form."""
        category = self.get_object(pk)
        form = TargetCategoryForm(instance=category, current_day=category.day)
        
        context = {
            'form': form,
            'object': category,
            'page_title': f'Update Category: {category.name}',
            'submit_text': 'Update Category',
            'is_update': True
        }
        
        return render(request, 'better/category_form.html', context)
    
    def post(self, request, pk):
        """Update category."""
        category = self.get_object(pk)
        form = TargetCategoryForm(request.POST, instance=category, current_day=category.day)
        
        if form.is_valid():
            updated_category = form.save()
            
            messages.success(
                request, 
                f'Category "{updated_category.name}" has been updated successfully.'
            )
            
            return redirect('better:dashboard')
        
        # Form has errors, re-render with errors
        context = {
            'form': form,
            'object': category,
            'page_title': f'Update Category: {category.name}',
            'submit_text': 'Update Category',
            'is_update': True
        }
        
        return render(request, 'better/category_form.html', context)


class TargetCategoryDeleteView(View):
    """Delete target categories using soft delete."""
    
    def get_object(self, pk):
        """Get category for today."""
        current_day = ScoreDay.get_or_create_today()
        return get_object_or_404(
            TargetCategory,
            pk=pk,
            day=current_day,
            is_deleted=False
        )
    
    def get(self, request, pk):
        """Show delete confirmation page."""
        category = self.get_object(pk)
        
        # Get count of targets that will be affected
        target_count = category.targets.filter(is_deleted=False).count()
        
        context = {
            'object': category,
            'page_title': f'Delete Category: {category.name}',
            'target_count': target_count,
            'category_name': category.name
        }
        
        return render(request, 'better/category_confirm_delete.html', context)
    
    def post(self, request, pk):
        """Soft delete category and its targets."""
        category = self.get_object(pk)
        category_name = category.name
        
        # Soft delete the category
        category.is_deleted = True
        category.save()
        
        # Soft delete all associated targets
        category.targets.filter(is_deleted=False).update(is_deleted=True)
        
        # Recalculate scores after deletion
        category.day.calculate_scores()
        
        messages.success(
            request, 
            f'Category "{category_name}" and all its targets have been removed successfully.'
        )
        
        return redirect('better:dashboard')


class TargetCreateView(View):
    """Create new targets within categories."""
    
    def get_initial_data(self, request):
        """Pre-select category from URL parameter."""
        initial = {}
        category_id = request.GET.get('category')
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
    
    def get(self, request):
        """Show target creation form."""
        current_day = ScoreDay.get_or_create_today()
        initial = self.get_initial_data(request)
        form = TargetForm(initial=initial, current_day=current_day)
        
        context = {
            'form': form,
            'page_title': 'Create New Target',
            'submit_text': 'Create Target',
            'current_day': current_day,
            'categories_count': current_day.categories.filter(is_deleted=False).count(),
            'importance_levels': Importance.objects.all().order_by('-score')
        }
        
        return render(request, 'better/target_form.html', context)
    
    def post(self, request):
        """Create new target."""
        current_day = ScoreDay.get_or_create_today()
        form = TargetForm(request.POST, current_day=current_day)
        
        if form.is_valid():
            # Set default values before saving
            target = form.save(commit=False)
            target.is_achieved = False  # Initialize as not achieved
            target.save()
            
            messages.success(
                request, 
                f'Target "{target.name}" has been created successfully in category "{target.category.name}".'
            )
            
            return redirect('better:dashboard')
        
        # Form has errors, re-render with errors
        context = {
            'form': form,
            'page_title': 'Create New Target',
            'submit_text': 'Create Target',
            'current_day': current_day,
            'categories_count': current_day.categories.filter(is_deleted=False).count(),
            'importance_levels': Importance.objects.all().order_by('-score')
        }
        
        return render(request, 'better/target_form.html', context)


class TargetAchievementView(View):
    """Toggle target achievement status with HTMX support."""
    
    def post(self, request, pk):
        """Toggle target achievement and recalculate scores."""
        try:
            # Get target and ensure it belongs to current day and is not deleted
            current_day = ScoreDay.get_or_create_today()
            target = get_object_or_404(
                Target,
                pk=pk,
                category__day=current_day,
                is_deleted=False
            )
            
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
                response = render(request, 'cotton/better/today_scores.html', context)
                
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
                return render(request, 'cotton/better/error_message.html', {
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
        
        except Exception:
            error_message = 'An error occurred while updating the target.'
            
            # Handle HTMX requests
            if request.headers.get('HX-Request'):
                return render(request, 'cotton/better/error_message.html', {
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
        """Get context data for today-scores component."""
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
        """Redirect to dashboard for security."""
        messages.info(request, 'Target achievement can only be updated via form submission.')
        return redirect('better:dashboard')


class ImportanceManagementView(View):
    """Manage importance levels with CRUD operations."""
    
    def get(self, request):
        """Display importance levels and creation form."""
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
        """Handle create, update, and delete actions for importance levels."""
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
        """Create new importance level."""
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
        """Update existing importance level."""
        importance_id = request.POST.get('importance_id')
        
        if not importance_id:
            messages.error(request, 'No importance level specified for update.')
            return redirect('better:importance-manage')
        
        try:
            importance = get_object_or_404(Importance, id=importance_id)
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
        except Exception:
            messages.error(request, 'An error occurred while updating the importance level.')
            return redirect('better:importance-manage')
    
    def _handle_delete(self, request):
        """Delete importance level."""
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
        except Exception:
            messages.error(request, 'An error occurred while deleting the importance level.')
            return redirect('better:importance-manage')


class DayView(View):
    """Display specific day's scores and targets."""
    
    def get(self, request, pk):
        """Display specific day's data."""
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
        """Update sleep/wake times for specific day."""
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

