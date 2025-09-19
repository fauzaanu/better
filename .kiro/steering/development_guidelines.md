# Development Guidelines

## Package Management
- Always use `uv` for package management
- To install packages: `uv add <package_name>`

## Command Restrictions
**IMPORTANT**: The following commands are STRICTLY PROHIBITED:

### NEVER RUN:
- `python manage.py runserver` - The server is always running
- `python manage.py test` - Tests should not be run automatically
- `python manage.py migrate` - Migration commands are not allowed
- `python manage.py shell` - Shell commands are not allowed
- Any other Django management commands except `check`
- Direct Python script execution

### ONLY ALLOWED COMMAND:
- `uv run python manage.py check` - This is the ONLY management command permitted

## Development Approach
- Focus on code changes and implementation
- Let the user handle command execution
- Do not run migrations, tests, or server commands
- Avoid any direct script execution