# startapp.py
import os
import re
from django.core.management.commands.startapp import Command as StartAppCommand


class Command(StartAppCommand):
    help = (
        "Like startapp, but always under apps/, "
        "with AppConfig.name='apps.<appname>' and auto-added to FIRST_PARTY_APPS."
    )

    def add_to_settings(self, app_name):
        base_path = os.path.join('onlydjango', 'settings', 'base.py')
        if os.path.exists(base_path):
            content = open(base_path, 'r').read().splitlines(keepends=True)
            out = []
            injected = False
            for line in content:
                if (not injected
                        and re.match(r'\s*FIRST_PARTY_APPS\s*=.*\[\s*', line)
                ):
                    out.append(line)
                    # keep app entries until closing bracket
                    continue
                if (not injected
                        and re.match(r'\s*\]', line)
                        and 'FIRST_PARTY_APPS' not in line
                ):
                    indent = re.match(r'^(\s*)\]', line).group(1)
                    out.append(f"{indent}'apps.{app_name}',\n")
                    injected = True
                out.append(line)
            if injected:
                open(base_path, 'w').write(''.join(out))
                self.stdout.write(self.style.SUCCESS(
                    f"Added 'apps.{app_name}' to FIRST_PARTY_APPS in base.py"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    "Could not find FIRST_PARTY_APPS to inject into."
                ))
        else:
            self.stdout.write(self.style.WARNING(
                f"Settings file not found at {base_path}"
            ))

    def patch_into_apps(self, app_name, target_dir):
        apps_py = os.path.join(target_dir, 'apps.py')
        text = open(apps_py, 'r').read()
        text = re.sub(
            r"name\s*=\s*['\"][\w\.]+['\"]",
            f"name = 'apps.{app_name}'",
            text
        )
        open(apps_py, 'w').write(text)

    def handle(self, *args, **options):
        app_name = options['name']

        os.makedirs('apps', exist_ok=True)
        init_py = os.path.join('apps', '__init__.py')
        if not os.path.exists(init_py):
            open(init_py, 'w').close()

        target_dir = os.path.join('apps', app_name)
        options['directory'] = target_dir
        os.makedirs(target_dir, exist_ok=True)
        super().handle(*args, **options)

        self.patch_into_apps(app_name, target_dir)

        self.add_to_settings(app_name)
