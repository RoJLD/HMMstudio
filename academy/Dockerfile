# --- build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# --- serve stage ---
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
# nginx:alpine runs every executable in /docker-entrypoint.d/ before starting.
COPY docker-entrypoint.sh /docker-entrypoint.d/40-academy-config.sh
RUN chmod +x /docker-entrypoint.d/40-academy-config.sh
EXPOSE 80
