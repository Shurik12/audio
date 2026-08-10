FROM node:18-alpine AS builder

WORKDIR /app

# Копирование package.json и установка зависимостей
COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps || npm install --legacy-peer-deps

# Копирование исходного кода и сборка
COPY . .
RUN npm run build

# Продакшен образ с Nginx
FROM nginx:alpine

# Копирование собранных файлов в Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Удаляем строку COPY nginx.conf, так как конфигурация будет из volumes
# COPY nginx.conf /etc/nginx/nginx.conf  # <-- УДАЛИТЬ ЭТУ СТРОКУ

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]