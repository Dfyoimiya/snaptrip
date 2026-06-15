# ===== SnapTrip Mall-Web (Vue 3 + Vite + Tailwind) =====
# C-end Shopping Portal
#
# 多阶段构建:
#   development — Vite dev server with HMR
#   production  — static build + nginx

# ==================== Base ====================
FROM node:22-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

ARG VITE_API_BASE_URL=http://localhost:8080
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# ==================== Development ====================
FROM base AS development
COPY . .
ENV VITE_APP_ENV=development
EXPOSE 5175
CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "5175"]

# ==================== Builder ====================
FROM base AS builder
COPY . .
RUN npm run build

# ==================== Production ====================
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
