from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.http import JsonResponse, Http404
from datetime import timedelta
from .models import ScoreDay, TargetCategory, Target, Importance
from .forms import TargetCategoryForm, SleepWakeTimeForm


class DashboardView(View):
    """Display today's dashboard with scores and targets."""
    
    def get(self, request):
        """Display dashboard with today's and yesterday's data."""
        current_day = ScoreDay.get_or_create_today()
        context = current_day.get_dashboard_context()
        return render(request, "better/dashboard.html", context)
    
    def post(self, request):
        """Update sleep and wake times."""
        current_day = ScoreDay.get_or_create_today()
        sleep_wake_form = SleepWakeTimeForm(data=request.POST, instance=current_day)
        
        if sleep_wake_form.is_valid():
            sleep_wake_form.save()
            messages.success(request, 'Sleep/wake times updated successfully.')
            return redirect('better:dashboard')
        
        # Re-render with form errors
        context = current_day.get_dashboard_context(sleep_wake_form)
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
    
    def get(self, request, pk):
        """Show category update form."""
        category = TargetCategory.get_for_today(pk)
        context = category.get_update_context()
        return render(request, 'better/category_form.html', context)
    
    def post(self, request, pk):
        """Update category."""
        category = TargetCategory.get_for_today(pk)
        updated_category, success_message, error_context = category.update_from_form(request.POST)
        
        if updated_category:
            messages.success(request, success_message)
            return redirect('better:dashboard')
        
        # Form has errors, re-render with errors
        return render(request, 'better/category_form.html', error_context)


class TargetCategoryDeleteView(View):
    """Delete target categories using soft delete."""
    
    def get(self, request, pk):
        """Show delete confirmation page."""
        category = TargetCategory.get_for_today(pk)
        context = category.get_delete_context()
        return render(request, 'better/category_confirm_delete.html', context)
    
    def post(self, request, pk):
        """Soft delete category and its targets."""
        category = TargetCategory.get_for_today(pk)
        success_message = category.soft_delete_with_targets()
        messages.success(request, success_message)
        return redirect('better:dashboard')


class TargetCreateView(View):
    """Create new targets within categories."""
    
    def get(self, request):
        """Show target creation form."""
        current_day = ScoreDay.get_or_create_today()
        category_id = request.GET.get('category')
        context = Target.get_create_context(current_day, category_id)
        return render(request, 'better/target_form.html', context)
    
    def post(self, request):
        """Create new target."""
        current_day = ScoreDay.get_or_create_today()
        target, error_form = Target.create_from_form(request.POST, current_day)
        
        if target:
            messages.success(
                request, 
                f'Target "{target.name}" has been created successfully in category "{target.category.name}".'
            )
            return redirect('better:dashboard')
        
        # Form has errors, re-render with errors
        context = Target.get_create_context(current_day)
        context['form'] = error_form  # Replace form with error form
        return render(request, 'better/target_form.html', context)


class TargetAchievementView(View):
    """Toggle target achievement status with HTMX support."""
    
    def post(self, request, pk):
        """Toggle target achievement and recalculate scores."""
        try:
            current_day = ScoreDay.get_or_create_today()
            target = Target.get_target_for_achievement(pk, current_day)
            
            # Toggle achievement status and trigger recalculation
            target.toggle_achievement()
            message = target.get_achievement_message()
            
            # Handle different request types
            return self._handle_response(request, target, current_day, message)
            
        except Http404:
            return self._handle_error(request, 'Target not found or no longer available.', 404)
        except Exception:
            return self._handle_error(request, 'An error occurred while updating the target.', 500)
    
    def _handle_response(self, request, target, current_day, message):
        """Handle different response types (HTMX, AJAX, regular)"""
        # Handle HTMX requests - return partial HTML template
        if request.headers.get('HX-Request'):
            context = current_day.get_dashboard_context()
            response = render(request, 'cotton/better/today_scores.html', context)
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
    
    def _handle_error(self, request, error_message, status_code):
        """Handle error responses for different request types"""
        # Handle HTMX requests
        if request.headers.get('HX-Request'):
            return render(request, 'cotton/better/error_message.html', {
                'error_message': error_message
            }, status=status_code)
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_message
            }, status=status_code)
        
        # Handle regular form submissions
        messages.error(request, error_message)
        return redirect('better:dashboard')
    
    def get(self, request, pk):
        """Redirect to dashboard for security."""
        messages.info(request, 'Target achievement can only be updated via form submission.')
        return redirect('better:dashboard')


class ImportanceManagementView(View):
    """Manage importance levels with CRUD operations."""
    
    def get(self, request):
        """Display importance levels and creation form."""
        context = Importance.get_management_context()
        return render(request, 'better/importance_management.html', context)
    
    def post(self, request):
        """Handle create, update, and delete actions for importance levels."""
        action = request.POST.get('action', 'create')
        result_type, message, context = Importance.handle_management_action(action, request.POST)
        
        if result_type == 'success':
            messages.success(request, message)
            return redirect('better:importance-manage')
        elif result_type == 'error':
            messages.error(request, message)
            return redirect('better:importance-manage')
        elif result_type == 'render':
            # Form validation errors - render with error context
            return render(request, 'better/importance_management.html', context)
        else:
            messages.error(request, 'An unexpected error occurred.')
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