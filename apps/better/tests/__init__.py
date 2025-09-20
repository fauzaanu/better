# Import all test modules to ensure they are discovered by Django's test runner
from . import test_models
from . import test_signals
from . import test_forms
from . import test_views

__all__ = ['test_models', 'test_signals', 'test_forms', 'test_views']