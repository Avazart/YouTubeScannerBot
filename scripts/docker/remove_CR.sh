#!/bin/bash
# Знаходимо всі файли з розширенням .sh у поточній директорії
sh_files=$(find . -name "*.sh")

# Виконуємо команду sed для кожного файла
for file in $sh_files; do
  sed -i 's/\r//g' "$file"
done
