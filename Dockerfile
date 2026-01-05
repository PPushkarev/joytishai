# 1. Используем официальный легковесный образ Python
FROM python:3.11-slim

# 2. Установка системных зависимостей
# Добавляем libmagic (часто нужен для LangChain/PDF) и curl для проверки здоровья
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Установка рабочей директории
WORKDIR /app

# 4. Копируем только requirements.txt для кэширования слоев
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копируем весь проект
COPY . .

# 6. Делаем entrypoint исполняемым (на случай, если Git на Windows сбросил права)
RUN chmod +x entrypoint.sh

# 7. Пробрасываем порт
EXPOSE 8000

# 8. Запуск через entrypoint.sh
# Теперь Docker выполнит все шаги: Индекс -> Судья -> Сервер
ENTRYPOINT ["/bin/sh", "entrypoint.sh"]