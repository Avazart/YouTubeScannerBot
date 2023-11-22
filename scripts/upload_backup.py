import sys
from pathlib import Path

from oauth2client.service_account import ServiceAccountCredentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

from get_ext_env import find_last_backup, load_dot_env


def upload_file(backup_file: Path, keyfile_path, email: str | None = None):
    gauth = GoogleAuth()
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        keyfile_path, ["https://www.googleapis.com/auth/drive"]
    )
    gauth.Authorize()
    drive = GoogleDrive(gauth)
    file_drive = drive.CreateFile(
        {
            "title": backup_file.name,
            # 'parents': [{'id': '16AjMFvyI2De8_DjZ2Ir0ZLRNMAcIxJSM'}]
        }
    )
    file_drive.SetContentFile(backup_file)
    file_drive.Upload()
    # Доступ по email
    if email:
        permission = file_drive.InsertPermission(  # noqa: F841
            {"type": "user", "value": email, "role": "writer"}
        )
    file_title = file_drive["title"]
    file_id = file_drive["id"]
    file_url = file_drive["alternateLink"]
    print(f"{file_title=}\n{file_id=}\n{file_url=}")


def main():
    scripts_dir = Path(__file__).parent
    project_dir = scripts_dir.parent
    assert len(sys.argv) == 2
    env_file = project_dir / sys.argv[1]
    env = load_dot_env(env_file)
    if keyfile_path := env.get("G_DISK_KEYFILE"):
        if backup_dir := env.get("BACKUP_DIR"):
            if last_backup := find_last_backup(project_dir / backup_dir):
                email = env.get("EMAIL")
                print(last_backup, email)
                upload_file(last_backup, project_dir / keyfile_path, email)
        else:
            raise RuntimeError("BACKUP_DIR not set!")
    else:
        raise RuntimeError("G_DISK_KEYFILE not set!")


if __name__ == "__main__":
    main()
