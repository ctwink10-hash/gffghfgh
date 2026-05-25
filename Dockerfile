# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем системные библиотеки, нужные для Pillow
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы проекта
WORKDIR /app
COPY . .

# Устанавливаем зависимости из вашего файла
RUN pip install --no-cache-dir -r requirements.txt

# Команда запуска
CMD ["python", "bot3.py"]
