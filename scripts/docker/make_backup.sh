cd ../..

source ./scripts/docker/set_env.sh

export NEW_BACKUP_PATH=$(python3 ./scripts/backup.py --dir $BACKUP_DIR new)

echo $NEW_BACKUP_PATH

docker exec --env-file $ENV_FILE -it postgres pg_dump \
--schema=public \
--format=p \
--inserts > $NEW_BACKUP_PATH