# ===== SnapTrip Frontend (Vue 3 + Vite + Element Plus) =====
# B-end Admin Portal
#
# 多阶段构建:
#   development — Vite dev server with HMR
#   production  — static build + nginx

# ==================== Base ====================
FROM node:22-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ==================== Development ====================
FROM base AS development
COPY . .
ENV VITE_APP_ENV=development
CMD ["npx", "vite", "--host", "0.0.0.0"]

# ==================== Builder ====================
FROM base AS builder
COPY . .
RUN npm run build

# ==================== Production ====================
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
