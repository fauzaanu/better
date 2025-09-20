# Testing views

- When testing views each view should have its own TestClass
- Test classes can have a base test class where all the setup is taken care of
- get and post are the main tests, but different scenerios should be well tested
- Do not take testing too far and test the individual functions the views are calling and stuff. (focus should be on request -> response)
- Given a request, do we get the following response? Does the database objects get created? Is it using the right django template? Is the context exactly as we expect?
- For authentication, use the base test class instead of doing it per test. This also assumes you follow the view convention of always keeping a base class based view where authentication is taken care of.
- And if all views use that base view where authentication is taken care of we have nothing to worry about.