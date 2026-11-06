FROM node:22-alpine AS build
WORKDIR /app
COPY platform/frontend/package*.json platform/frontend/
RUN cd platform/frontend && npm ci
COPY platform/frontend platform/frontend
COPY web web
ARG NEXT_PUBLIC_DATA_BASE=http://localhost:8000/api/snapshots
ENV NEXT_PUBLIC_DATA_BASE=$NEXT_PUBLIC_DATA_BASE NEXT_PUBLIC_BASE_PATH="" NEXT_TELEMETRY_DISABLED=1
RUN cd platform/frontend && npm run build -- --webpack
FROM nginx:alpine
COPY --from=build /app/platform/frontend/out /usr/share/nginx/html
EXPOSE 80
