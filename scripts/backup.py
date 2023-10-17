import argparse
import re
from datetime import datetime
from pathlib import Path

DT_FORMAT = '%Y_%m_%d_%H_%M'
PATTERN = re.compile(r'(\d{4}_\d{2}_\d{2}_\d{2}_\d{2})\.sql')


def new_backup(args):
    backup_path = args.dir / f'{datetime.now():{DT_FORMAT}}.sql'
    print(str(backup_path), end="")


def last_backup(args):
    backup_files = [
        p for p in args.dir.glob('*.sql') if PATTERN.match(p.name)
    ]

    def get_key(p: Path) -> datetime:
        m = PATTERN.match(p.name)
        assert m
        return datetime.strptime(m.group(1), DT_FORMAT)

    backup_files.sort(key=get_key, reverse=True)
    if backup_files:
        print(str(backup_files[1]), end="")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', type=Path, required=True)
    subparsers = parser.add_subparsers(help='List of commands:')

    # GENERATE NEW BACKUP PATH
    new_backup_path_parser = subparsers.add_parser(
        'new',
        help='generate path to new backup file with current datetime'
    )
    new_backup_path_parser.set_defaults(
        func=new_backup
    )

    # GET LAST BACKUP IN DIR
    last_backup_parser = subparsers.add_parser(
        'last',
        help='return last backup file in backups directory'
    )
    last_backup_parser.set_defaults(
        func=last_backup
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
