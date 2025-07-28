## Template Organization Convention

When organizing templates for Django applications, follow these conventions:

1. **Components vs Pages**:
   - `templates/cotton/<app_name>/` - For reusable components
   - `templates/<app_name>/` - For actual pages rendered by views

2. **Component Naming Convention**:
   - Use dot notation instead of hyphens for folder references: `<c-app_name.component_name>` 
   - Example: Use `<c-gt-manager.layout>` instead of `<c-sc-layout>`

3. **Template Structure**:
   - Views should normally reference a direct page from `templates/<app_name>/`
   - Pages can contain components from `templates/cotton/<app_name>/`
   - The only exception is when using an HTML component where we just re-render the component alone

This organization helps maintain a clear separation between reusable components and full pages.
