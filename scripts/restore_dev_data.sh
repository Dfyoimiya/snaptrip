#!/usr/bin/env bash
# ==============================================================================
# 开发数据恢复脚本 —— 从 tar.gz 归档恢复 PostgreSQL + MinIO 数据
#
# 用法:
#   ./scripts/restore_dev_data.sh snaptrip_dev_data_20240624_120000.tar.gz
#   ./scripts/restore_dev_data.sh archive.tar.gz --db-only
#   ./scripts/restore_dev_data.sh archive.tar.gz --minio-only
#   ./scripts/restore_dev_data.sh archive.tar.gz --dry-run       # 仅查看内容
#
# 注意: 恢复操作会覆盖现有数据，请谨慎使用
# ==============================================================================

set -euo pipefail

# ── 默认配置 ──
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DB_ONLY=false
MINIO_ONLY=false
DRY_RUN=false
FORCE=false

# ── 容器/连接配置 ──
DB_CONTAINER="snaptrip-db"
MINIO_CONTAINER="snaptrip-minio"
DB_USER="${POSTGRES_USER:-snaptrip}"
DB_NAME="${POSTGRES_DEV_DB:-snaptrip_dev}"
MINIO_BUCKET="${OSS_BUCKET:-snaptrip-commerce}"
MINIO_ALIAS="local"
MINIO_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_PASS="${MINIO_ROOT_PASSWORD:-minioadmin}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }
info() { echo -e "${CYAN}[INFO]${NC} $*"; }

usage() {
    cat <<EOF
用法: $0 <archive.tar.gz> [选项]

参数:
  archive.tar.gz   由 dump_dev_data.sh 生成的归档文件

选项:
  --db-only         仅恢复 PostgreSQL 数据库
  --minio-only      仅恢复 MinIO 对象存储
  --dry-run         仅查看归档内容，不执行恢复
  --force           跳过确认提示，直接恢复
  -h, --help        显示帮助
EOF
    exit 0
}

# ── 参数解析 ──
ARCHIVE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --db-only) DB_ONLY=true; shift ;;
        --minio-only) MINIO_ONLY=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --force) FORCE=true; shift ;;
        -h|--help) usage ;;
        -*)
            err "未知参数: $1"
            usage
            ;;
        *)
            if [ -z "$ARCHIVE" ]; then
                ARCHIVE="$1"
            else
                err "多余的参数: $1"
                usage
            fi
            shift
            ;;
    esac
done

if $DB_ONLY && $MINIO_ONLY; then
    err "--db-only 和 --minio-only 不能同时使用"
    exit 1
fi

if [ -z "$ARCHIVE" ]; then
    err "缺少归档文件参数"
    echo ""
    usage
fi

if [ ! -f "$ARCHIVE" ]; then
    err "归档文件不存在: $ARCHIVE"
    exit 1
fi

# ── 检查容器运行状态 ──
check_container() {
    local name="$1"
    if ! docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
        err "容器未运行: $name"
        err "请先启动: make dev"
        exit 1
    fi
}

# ── 预览归档 ──
preview_archive() {
    echo ""
    echo "=========================================="
    echo "  归档内容预览"
    echo "=========================================="
    echo ""
    echo "文件: $ARCHIVE"
    echo "大小: $(du -h "$ARCHIVE" | cut -f1)"
    echo ""

    echo "内容列表:"
    tar tzf "$ARCHIVE" 2>/dev/null | head -50

    local total_files
    total_files=$(tar tzf "$ARCHIVE" 2>/dev/null | wc -l)
    if [ "$total_files" -gt 50 ]; then
        echo "  ... 及其他 $((total_files - 50)) 个文件"
    fi

    echo ""
    if tar tzf "$ARCHIVE" 2>/dev/null | grep -q "database.dump"; then
        local db_size
        db_size=$(tar tzvf "$ARCHIVE" 2>/dev/null | grep "database.dump" | awk '{print $3}')
        echo "数据库: 有 (database.dump, ${db_size} bytes)"
    else
        echo "数据库: 无"
    fi

    if tar tzf "$ARCHIVE" 2>/dev/null | grep -q "/minio/"; then
        local minio_count
        minio_count=$(tar tzf "$ARCHIVE" 2>/dev/null | grep "/minio/" | wc -l)
        echo "MinIO:   有 (${minio_count} 个对象)"
    else
        echo "MinIO:   无"
    fi
    echo ""
}

# ── restore_database ──
restore_database() {
    local work_dir="$1"
    local dump_file="${work_dir}/database.dump"

    if [ ! -f "$dump_file" ]; then
        warn "归档中没有数据库文件 (database.dump)，跳过数据库恢复"
        return 0
    fi

    log "恢复 PostgreSQL 数据库..."

    check_container "$DB_CONTAINER"

    if $DRY_RUN; then
        log "[DRY RUN] 将恢复数据库: $dump_file"
        return 0
    fi

    # 复制 dump 文件到容器
    docker cp "$dump_file" "${DB_CONTAINER}:/tmp/snaptrip_restore.dump"

    # 获取当前数据库中的表
    local current_tables
    current_tables=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "?")

    info "当前数据库有 $current_tables 张表"

    # 恢复 (--clean --if-exists 先删除已有对象)
    log "执行 pg_restore..."
    set +e
    local restore_output
    restore_output=$(docker exec "$DB_CONTAINER" pg_restore \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --clean \
        --if-exists \
        --no-owner \
        --no-acl \
        --single-transaction \
        /tmp/snaptrip_restore.dump 2>&1)
    local restore_exit=$?
    set -e

    if [ "$restore_exit" -eq 0 ]; then
        log "数据库恢复成功"
    else
        warn "pg_restore 有一些警告 (可能是首次导入，正常)"
        [ -n "$restore_output" ] && warn "pg_restore: $restore_output"
        log "数据库恢复完成 (exit=$restore_exit)"
    fi

    docker exec "$DB_CONTAINER" rm -f /tmp/snaptrip_restore.dump
}

# ── restore_minio ──
restore_minio() {
    local work_dir="$1"
    local minio_dir="${work_dir}/minio"

    if [ ! -d "$minio_dir" ] || [ -z "$(ls -A "$minio_dir" 2>/dev/null)" ]; then
        warn "归档中没有 MinIO 数据，跳过 MinIO 恢复"
        return 0
    fi

    log "恢复 MinIO 对象存储..."

    check_container "$MINIO_CONTAINER"

    # 配置 mc alias
    docker exec "$MINIO_CONTAINER" mc alias set "$MINIO_ALIAS" \
        "http://localhost:9000" "$MINIO_USER" "$MINIO_PASS" >/dev/null 2>&1

    # 确保 bucket 存在
    if ! docker exec "$MINIO_CONTAINER" mc ls "${MINIO_ALIAS}/${MINIO_BUCKET}" >/dev/null 2>&1; then
        log "创建 MinIO bucket: ${MINIO_BUCKET}"
        docker exec "$MINIO_CONTAINER" mc mb "${MINIO_ALIAS}/${MINIO_BUCKET}" 2>/dev/null || true
    fi

    local obj_count
    obj_count=$(find "$minio_dir" -type f | wc -l)
    info "归档中包含 ${obj_count} 个 MinIO 对象"

    if $DRY_RUN; then
        log "[DRY RUN] 将恢复 MinIO bucket: $MINIO_BUCKET (${obj_count} objects)"
        return 0
    fi

    # 使用 docker cp 传输到容器 (容器内不含 tar)
    local tmp_dir="/tmp/minio_import_$(date +%s)"
    docker exec "$MINIO_CONTAINER" mkdir -p "$tmp_dir"

    log "传输 MinIO 数据到容器 (${obj_count} objects) ..."
    docker cp "${minio_dir}/." "${MINIO_CONTAINER}:${tmp_dir}/" 2>/dev/null

    # Mirror 到 bucket (--overwrite 确保覆盖已有文件)
    log "写入 MinIO bucket..."
    set +e
    local mc_stderr
    mc_stderr=$(docker exec "$MINIO_CONTAINER" mc mirror --quiet --overwrite \
        "$tmp_dir" "${MINIO_ALIAS}/${MINIO_BUCKET}" 2>&1 >/dev/null)
    local mc_exit=$?
    set -e

    docker exec "$MINIO_CONTAINER" rm -rf "$tmp_dir" 2>/dev/null || true

    if [ "$mc_exit" -ne 0 ]; then
        err "mc mirror 失败 (exit code: $mc_exit)"
        [ -n "$mc_stderr" ] && warn "mc: $mc_stderr"
        return 1
    fi

    log "MinIO 恢复完成 (${obj_count} objects)"
}

# ── 确认提示 ──
confirm_restore() {
    if $FORCE || $DRY_RUN; then
        return 0
    fi

    echo ""
    warn "=============================================="
    warn "  ⚠️  警告: 此操作将覆盖现有数据库和MinIO数据!"
    warn "=============================================="
    echo ""

    read -r -p "确认恢复? 输入 'yes' 继续: " confirm
    if [ "$confirm" != "yes" ]; then
        echo "已取消"
        exit 0
    fi
    echo ""
}

# ── 主流程 ──
main() {
    preview_archive

    if $DRY_RUN; then
        log "[DRY RUN] 完成"
        exit 0
    fi

    confirm_restore

    # 创建临时工作目录
    local work_dir
    work_dir=$(mktemp -d -t snaptrip_restore_XXXXXX)
    trap 'rm -rf "$work_dir"' EXIT

    log "解压归档文件..."
    tar xzf "$ARCHIVE" -C "$work_dir"

    local do_db=true
    local do_minio=true

    if $DB_ONLY; then
        do_minio=false
    elif $MINIO_ONLY; then
        do_db=false
    fi

    # 恢复顺序: 先DB后MinIO (MinIO不依赖DB)
    if $do_db; then
        restore_database "$work_dir"
    fi

    if $do_minio; then
        restore_minio "$work_dir"
    fi

    echo ""
    log "✅ 恢复完成!"

    if $do_db; then
        info "  - PostgreSQL: snaptrip-db / $DB_NAME"
    fi
    if $do_minio; then
        info "  - MinIO:  http://localhost:9001 (console)"
        info "    bucket: $MINIO_BUCKET"
    fi
    echo ""
}

main
