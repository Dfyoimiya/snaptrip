# SnapTrip 单机生产部署

这套配置面向 Ubuntu 22.04/24.04 云服务器，使用 Docker Compose 运行应用服务，
由宿主机 Nginx 负责域名、HTTPS 和 SSE 反向代理。

## 1. 服务器要求

- 推荐 8 核 16 GB；最低建议 4 核 8 GB
- 磁盘建议 60 GB 以上
- 防火墙仅向公网开放 22、80、443
- PostgreSQL、Redis、Elasticsearch、LiteLLM 和应用端口都只绑定 `127.0.0.1`

## 2. 安装依赖

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
```

重新登录 SSH，使 Docker 用户组生效。

## 3. 域名解析

创建两条 A 记录并指向服务器公网 IP：

```text
snaptrip.example.com
admin.snaptrip.example.com
```

## 4. 环境变量

```bash
cp .env.production.example .env
openssl rand -hex 32
```

将命令执行三次，分别填写 `APP_SECRET_KEY`、`JWT_SECRET_KEY` 和
`LITELLM_MASTER_KEY`。同时填写数据库、Redis 和模型供应商密钥，并将示例域名
替换为真实域名。

## 5. 准备本地向量模型

搜索服务以离线模式加载 `all-MiniLM-L6-v2`。服务器首次部署前应准备模型缓存：

```bash
sudo mkdir -p /opt/snaptrip/huggingface
sudo chown -R "$USER":"$USER" /opt/snaptrip
```

将开发机的 Hugging Face 缓存同步到 `.env` 中 `HF_MODEL_CACHE` 指定的目录，
或者在联网环境预下载 `sentence-transformers/all-MiniLM-L6-v2`。该目录必须对
Docker 容器内的非 root 用户可读。

## 6. 启动应用

生产命令显式指定 Compose 文件，不会自动混入本地开发覆盖文件：

```bash
docker compose -f docker-compose.yml --profile full config
docker compose -f docker-compose.yml --profile full build
docker compose -f docker-compose.yml --profile full up -d
docker compose -f docker-compose.yml --profile full ps
```

首次启动会自动执行 `alembic upgrade head`。

本机检查：

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:5174/health
curl http://127.0.0.1:5175/health
```

## 7. 配置 Nginx 和 HTTPS

```bash
sudo cp deploy/nginx/snaptrip.conf.example /etc/nginx/sites-available/snaptrip
sudo sed -i 's/__SITE_DOMAIN__/你的商城域名/g' /etc/nginx/sites-available/snaptrip
sudo sed -i 's/__ADMIN_DOMAIN__/你的管理端域名/g' /etc/nginx/sites-available/snaptrip
sudo ln -s /etc/nginx/sites-available/snaptrip /etc/nginx/sites-enabled/snaptrip
sudo nginx -t
sudo systemctl reload nginx
```

确认 HTTP 可以访问后申请证书：

```bash
sudo certbot --nginx -d 你的商城域名 -d 你的管理端域名
sudo certbot renew --dry-run
```

Nginx 的 `/api/` 已关闭代理缓冲并延长读取超时，适配 Agent 和客服 SSE。

## 8. 发布更新

```bash
git pull --ff-only
docker compose -f docker-compose.yml --profile full build
docker compose -f docker-compose.yml --profile full up -d
docker compose -f docker-compose.yml --profile full ps
```

查看日志：

```bash
docker compose -f docker-compose.yml --profile full logs --tail=200 marketplace
docker compose -f docker-compose.yml --profile full logs --tail=200 agent-worker
```

## 9. 数据备份

```bash
mkdir -p backups
docker compose -f docker-compose.yml exec -T postgres \
  pg_dump -U snaptrip snaptrip | gzip > "backups/snaptrip-$(date +%F-%H%M).sql.gz"
```

生产环境应通过 cron 或云厂商快照定期备份 PostgreSQL 数据卷。
