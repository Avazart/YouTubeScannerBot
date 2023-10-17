cd ../..

source ./scripts/docker/set_env.sh
echo $PSQL_PATH

export DELETE_VIDEOS="scripts/delete_videos.sql"

cat $DELETE_VIDEOS | docker exec --env-file $ENV_FILE -i postgres $PSQL_PATH


