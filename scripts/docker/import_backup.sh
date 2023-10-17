cd ../..

source ./scripts/docker/set_env.sh

export LAST_BACKUP_PATH=$(python3 scripts/backup.py --dir $BACKUP_DIR last)

echo $LAST_BACKUP_PATH

export DROP_SCHEMA_FILE=scripts/drop_schema.sql

cat $DROP_SCHEMA_FILE | docker exec --env-file $ENV_FILE -i postgres psql
cat $LAST_BACKUP_PATH | docker exec --env-file $ENV_FILE -i postgres psql