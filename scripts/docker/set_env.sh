export ENV_FILE=.env.prod

echo "Set environment ..."

while IFS= read -r line; do
   #line=$(echo "$line" | sed -e 's/[[:space:]]*$//')
   #echo "$line"
   export "$line"
done < <(python3 ./scripts/get_ext_env.py $ENV_FILE)
