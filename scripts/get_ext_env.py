import re
import sys
import urllib
import urllib.parse
from datetime import datetime
from pathlib import Path

DT_FORMAT = "%Y_%m_%d_%H_%M"
PATTERN = re.compile(r"(\d{4}_\d{2}_\d{2}_\d{2}_\d{2})\.sql")


def load_dot_env(env_file: Path) -> dict[str, str]:
    env = {}
    with env_file.open(encoding="utf-8") as file:
        for line in file:
            if line := line.strip():
                try:
                    key, value = line.split("=", maxsplit=1)
                    env[key] = value
                except ValueError:
                    pass
    return env


def find_last_backup(backup_dir: Path) -> Path | None:
    backup_files = [
        p for p in backup_dir.glob("*.sql") if PATTERN.match(p.name)
    ]

    def get_key(p: Path) -> datetime:
        m = PATTERN.match(p.name)
        assert m
        return datetime.strptime(m.group(1), DT_FORMAT)

    backup_files.sort(key=get_key, reverse=True)
    if backup_files:
        return backup_files[0]
    return None


def add_pair(key, value, d: dict):
    if value:
        d[key] = value if isinstance(value, str) else str(value)


def parse_url(url: str) -> dict[str, str]:
    result = urllib.parse.urlparse(url)
    db_vars = {}
    if "postgresql" in result.scheme:
        add_pair("DB_DRIVER", result.scheme, db_vars)
        add_pair("PGUSER", result.username, db_vars)
        add_pair("PGPASSWORD", result.password, db_vars)
        add_pair("PGHOST", result.hostname, db_vars)
        add_pair("PGPORT", result.port, db_vars)
        add_pair("PGDATABASE", result.path.removeprefix("/"), db_vars)
    else:
        # sqlite+aiosqlite:///example.db
        add_pair("SQLITE_DATABASE", result.path.removeprefix("/"), db_vars)
    return db_vars


def main():
    scripts_dir = Path(__file__).parent
    project_dir = scripts_dir.parent
    assert len(sys.argv) == 2
    env_file = project_dir / sys.argv[1]
    env = load_dot_env(env_file)

    if database_url := env.get("DATABASE_URL"):
        ext_env = parse_url(database_url)
        if backup_dir := env.get("BACKUP_DIR"):
            now = datetime.now()
            ext_env["NEW_BACKUP_PATH"] = str(
                Path(backup_dir) / f"{now:{DT_FORMAT}}.sql"
            )
            if last_backup := find_last_backup(project_dir / backup_dir):
                ext_env["LAST_BACKUP_PATH"] = str(
                    last_backup.relative_to(project_dir)
                )
        env |= ext_env

    for key, value in env.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
