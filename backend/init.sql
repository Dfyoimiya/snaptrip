CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- LiteLLM 网关数据库（消费追踪 + 虚拟密钥管理）
-- docker-entrypoint 在首次初始化时执行
SELECT 'CREATE DATABASE snaptrip_litellm'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'snaptrip_litellm')\gexec
