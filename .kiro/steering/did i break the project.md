To ensure that your changes did not break the project do the following one by one.

1. run `uv run ruff check --fix`
2. run `uv run python manage.py check`
3. run uv run python manage.py test`