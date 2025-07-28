import os
import shutil
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase


class StartAppCommandTests(SimpleTestCase):
    def setUp(self):
        # 1) spin up a temp dir & cd into it
        self.tmp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmp_dir)

        # 2) create onlydjango/settings/base.py with a FIRST_PARTY_APPS list
        settings_dir = os.path.join('onlydjango', 'settings')
        os.makedirs(settings_dir)
        base_py = os.path.join(settings_dir, 'base.py')
        with open(base_py, 'w') as f:
            f.write(
                "FIRST_PARTY_APPS = [\n"
                "    'django.contrib.admin',\n"
                "]\n"
            )

    def tearDown(self):
        # restore cwd & cleanup
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tmp_dir)

    def test_creates_apps_package_and_init(self):
        # before: no apps/
        self.assertFalse(os.path.exists('apps'))

        call_command('startapp', 'myapp', stdout=StringIO())

        # after: apps/ + __init__.py exist
        self.assertTrue(os.path.isdir('apps'))
        self.assertTrue(os.path.isfile(os.path.join('apps', '__init__.py')))

    def test_scaffolds_app_and_patches_apps_py(self):
        call_command('startapp', 'myapp', stdout=StringIO())
        app_dir = os.path.join('apps', 'myapp')
        self.assertTrue(os.path.isdir(app_dir))

        apps_py = os.path.join(app_dir, 'apps.py')
        self.assertTrue(os.path.isfile(apps_py))

        text = open(apps_py).read()
        self.assertIn("name = 'apps.myapp'", text)

    def test_injects_into_FIRST_PARTY_APPS(self):
        buf = StringIO()
        call_command('startapp', 'anotherapp', stdout=buf)

        base_py = os.path.join('onlydjango', 'settings', 'base.py')
        content = open(base_py).read()
        self.assertIn("'apps.anotherapp'", content)

        # success message
        self.assertIn("Added 'apps.anotherapp' to FIRST_PARTY_APPS", buf.getvalue())

    def test_warns_if_no_FIRST_PARTY_APPS(self):
        # overwrite base.py so it has no FIRST_PARTY_APPS
        base_py = os.path.join('onlydjango', 'settings', 'base.py')
        with open(base_py, 'w') as f:
            f.write("INSTALLED_APPS = []\n")

        buf = StringIO()
        call_command('startapp', 'thirdapp', stdout=buf)
        self.assertIn("Could not find FIRST_PARTY_APPS", buf.getvalue())
