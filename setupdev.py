import os
import sys
import subprocess
from dotenv import load_dotenv

REQUIRED = {
    "PGDATABASE": "postgres",
    "PGUSER": "postgres",
    "PGPASSWORD": "admin",
    "PGHOST": "localhost",
    "PGPORT": "5432",
}


def verify_env():
    for key, expected in REQUIRED.items():
        actual = os.getenv(key)
        if actual != expected:
            print(f"[ERROR] {key} expected '{expected}', got '{actual}'", file=sys.stderr)
            return False
    return True


def run(cmd):
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


def main():
    load_dotenv()

    if not verify_env():
        sys.exit(1)

    # tear down any running containers
    result = subprocess.run("docker ps -q", shell=True, check=True, stdout=subprocess.PIPE, text=True)
    for cid in result.stdout.split():
        run(f"docker rm -f {cid}")

    run("docker compose -f dev_helpers/dev.docker-compose.yml up -d")
    run("uv run python manage.py makemigrations")
    run("uv run python manage.py migrate")


if __name__ == "__main__":
    main()
