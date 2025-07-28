import ast
import os
import importlib

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

# ANSI highlighting
try:
    from colorama import init as _init_colorama, Fore, Style

    _init_colorama(autoreset=True)
except ImportError:
    Fore = Style = type("X", (object,), {
        "RED": "",
        "BRIGHT": "",
        "RESET_ALL": "",
    })()


def get_attr_chain(node):
    chain = []
    while isinstance(node, ast.Attribute):
        chain.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        chain.append(node.id)
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        chain.append(node.func.id)
    return list(reversed(chain))


def print_snippet(path, lineno, context=2, out_fn=print):
    """
    Print lines [lineno-context .. lineno+context] from file,
    highlighting line `lineno`.
    """
    try:
        lines = open(path, 'r', encoding='utf-8').read().splitlines()
    except OSError:
        return
    start = max(1, lineno - context)
    end = min(len(lines), lineno + context)
    out_fn(f"\n  → snippet from {os.path.basename(path)}, around line {lineno}:")
    for i in range(start, end + 1):
        prefix = f"{i:>4} | "
        text = lines[i - 1]
        if i == lineno:
            out_fn(f"    {Fore.RED}{Style.BRIGHT}> {prefix}{text}{Style.RESET_ALL}")
        else:
            out_fn(f"      {prefix}{text}")
    out_fn("")  # blank line


class Command(BaseCommand):
    help = 'Detect potential N+1 queries in model methods, with snippet highlighting and optional markdown report.'

    def add_arguments(self, parser):
        parser.add_argument('targets', nargs='*', help=(
            "Dot-notation Python paths (e.g. apps.dashboard) or "
            "filesystem paths. If omitted, scans all INSTALLED_APPS."), )
        parser.add_argument('-llm', action='store_true', help=(
            "Also generate a markdown report 'n_plus_one.md' in the project root "
            "listing all detected issues with a summary prompt."), )

    def handle(self, *args, **options):
        self.issues_count = 0
        self.issues_messages = []
        targets = options['targets']
        write_md = options['llm']

        if targets:
            for tgt in targets:
                if '.' in tgt:
                    try:
                        mod = importlib.import_module(tgt)
                    except ImportError as e:
                        raise CommandError(f"Could not import '{tgt}': {e}")
                    path = (mod.__path__[
                        0] if hasattr(mod, '__path__') else os.path.dirname(mod.__file__))
                    self._scan_path(path)
                else:
                    self._scan_path(tgt)
        else:
            for app_config in apps.get_app_configs():
                models_file = os.path.join(app_config.path, 'models.py')
                if os.path.isfile(models_file):
                    self._scan_file(models_file)

        # summary to console
        if self.issues_count == 0:
            self.stdout.write(self.style.SUCCESS("🎉 Congratulations! No potential N+1 queries found."))
        else:
            self.stdout.write(self.style.WARNING(f"⚠ Detected {self.issues_count} potential N+1 issue"
                                                 f"{'s' if self.issues_count != 1 else ''}"))

        # markdown report
        if write_md:
            md_path = os.path.join(os.getcwd(), 'n_plus_one.md')
            with open(md_path, 'w', encoding='utf-8') as md:
                md.write("# Potential N+1 Issues Report\n\n")
                md.write("_These are some potential possible N+1 issues and they may be real or maybe optimizable. "
                         "Please review each and optimize if possible._\n\n")
                if not self.issues_messages:
                    md.write("🎉 No issues detected! Your code appears clean.\n")
                else:
                    for msg in self.issues_messages:
                        md.write(f"- {msg}\n")
            self.stdout.write(self.style.SUCCESS(f"Markdown report written to {md_path}"))

    def _scan_path(self, path):
        if os.path.isdir(path):
            for dirpath, _, files in os.walk(path):
                if 'models.py' in files:
                    self._scan_file(os.path.join(dirpath, 'models.py'))
        elif os.path.isfile(path) and path.endswith('.py'):
            self._scan_file(path)
        else:
            raise CommandError(f"Path not found or not a .py file: {path}")

    def _scan_file(self, path):
        try:
            source = open(path, 'r', encoding='utf-8').read()
        except (IOError, OSError):
            return
        tree = ast.parse(source, path)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for member in node.body:
                if not isinstance(member, (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                )):
                    continue

                has_loop = any(isinstance(n, ast.For) for n in ast.walk(member))
                raw_qs_lines = []
                for n in ast.walk(member):
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                        chain = get_attr_chain(n.func)
                        if 'objects' in chain and 'select_related' not in chain and 'prefetch_related' not in chain:
                            raw_qs_lines.append(n.lineno)

                if has_loop and raw_qs_lines:
                    for ln in raw_qs_lines:
                        msg = (
                            f"{path}:{ln}  ⚠ Potential N+1 in `{member.name}`: "
                            "`.objects` without `select_related`/`prefetch_related` in a loop")
                        self.stdout.write(self.style.WARNING(msg))
                        print_snippet(path, ln, context=2, out_fn=self.stdout.write)
                        self.issues_messages.append(msg)
                        self.issues_count += 1
