FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ .
RUN npm run build -- --configuration=production

FROM nginx:alpine
COPY --from=build /app/dist/balanceiq-frontend/browser /usr/share/nginx/html
COPY docker/nginx-frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
