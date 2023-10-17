export ENV_FILE=.env.prod

# Читаємо .env файл і встановлюємо змінні оточення
while IFS= read -r line; do
   line=$(echo "$line" | sed -e 's/[[:space:]]*$//')
   export "$line"
done <  $ENV_FILE

export BACKUP_DIR="${APP_DATA}/backups"