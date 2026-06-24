#!/usr/bin/env bash
# ==============================================================================
# 开发数据导出脚本 —— 导出 PostgreSQL + MinIO 数据为可共享的 tar.gz 归档
#
# 用法:
#   ./scripts/dump_dev_data.sh                          # 默认: 完整导出
#   ./scripts/dump_dev_data.sh -o ~/Desktop/snap.tar.gz # 指定输出路径
#   ./scripts/dump_dev_data.sh --db-only                # 仅导出数据库
#   ./scripts/dump_dev_data.sh --minio-only             # 仅导出 MinIO
#   ./scripts/dump_dev_data.sh --tables pms_products,pms_skus  # 仅指定表
#
# 输出: snaptrip_dev_data_YYYYMMDD_HHMMSS.tar.gz
# ==============================================================================

set -euo pipefail

# ── 默认配置 ──
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DEFAULT_OUTPUT="${PROJECT_DIR}/snaptrip_dev_data_${TIMESTAMP}.tar.gz"

OUTPUT_FILE="$DEFAULT_OUTPUT"
DB_ONLY=false
MINIO_ONLY=false
SKIP_MINIO=false
SKIP_DB=false
SELECTED_TABLES=""
DRY_RUN=false

# ── 容器/连接配置 ──
DB_CONTAINER="snaptrip-db"
MINIO_CONTAINER="snaptrip-minio"
DB_USER="${POSTGRES_USER:-snaptrip}"
DB_NAME="${POSTGRES_DEV_DB:-snaptrip_dev}"
MINIO_BUCKET="${OSS_BUCKET:-snaptrip-commerce}"
MINIO_ALIAS="local"
MINIO_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_PASS="${MINIO_ROOT_PASSWORD:-minioadmin}"

# ── 颜色输出 ──
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
用法: $0 [选项]

选项:
  -o FILE        输出文件路径 (默认: snaptrip_dev_data_TIMESTAMP.tar.gz)
  --db-only       仅导出 PostgreSQL 数据库
  --minio-only    仅导出 MinIO 对象存储
  --tables LIST   仅导出指定表，逗号分隔 (如: pms_products,pms_skus)
  --dry-run       检查状态不执行导出
  -h, --help      显示帮助

环境变量:
  POSTGRES_USER     数据库用户 (默认: snaptrip)
  POSTGRES_DEV_DB   数据库名 (默认: snaptrip_dev)
  MINIO_ROOT_USER   MinIO 用户 (默认: minioadmin)
  MINIO_ROOT_PASS   MinIO 密码 (默认: minioadmin)
  OSS_BUCKET        MinIO Bucket (默认: snaptrip-commerce)
EOF
    exit 0
}

# ── 参数解析 ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        -o) OUTPUT_FILE="$2"; shift 2 ;;
        --db-only) DB_ONLY=true; shift ;;
        --minio-only) MINIO_ONLY=true; shift ;;
        --tables) SELECTED_TABLES="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        -h|--help) usage ;;
        *) err "未知参数: $1"; usage ;;
    esac
done

if $DB_ONLY && $MINIO_ONLY; then
    err "--db-only 和 --minio-only 不能同时使用"
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

# ── dump_database ──
dump_database() {
    local work_dir="$1"
    local dump_file="${work_dir}/database.dump"

    log "导出 PostgreSQL 数据库..."

    check_container "$DB_CONTAINER"

    # 构建 pg_dump 参数
    local table_args=""
    if [ -n "$SELECTED_TABLES" ]; then
        IFS=',' read -ra TABLES <<< "$SELECTED_TABLES"
        for tbl in "${TABLES[@]}"; do
            table_args="$table_args -t public.$tbl"
        done
        info "仅导出表: $SELECTED_TABLES"
    fi

    # 获取数据库大小用于报告
    local db_size
    db_size=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
        "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" 2>/dev/null || echo "未知")

    info "数据库大小: $db_size"

    if $DRY_RUN; then
        log "[DRY RUN] 将导出数据库到: $dump_file"
        return 0
    fi

    # 执行导出 (custom 格式，支持选择性恢复)
    # 注意: 不使用 pipefail 严格模式，因为 pg_dump 常有非错误 stderr 输出
    set +euo pipefail
    local dump_stderr
    dump_stderr=$(docker exec "$DB_CONTAINER" pg_dump \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --format=custom \
        --compress=9 \
        --no-owner \
        --no-acl \
        $table_args \
        -f /tmp/snaptrip_db.dump 2>&1 >/dev/null)
    local dump_exit=$?
    set -euo pipefail

    if [ "$dump_exit" -ne 0 ]; then
        err "pg_dump 失败 (exit code: $dump_exit)"
        [ -n "$dump_stderr" ] && warn "pg_dump: $dump_stderr"
        return 1
    fi
    [ -n "$dump_stderr" ] && warn "pg_dump: $dump_stderr"

    # 从容器复制到本地
    docker cp "${DB_CONTAINER}:/tmp/snaptrip_db.dump" "$dump_file"
    docker exec "$DB_CONTAINER" rm -f /tmp/snaptrip_db.dump

    local local_size
    local_size=$(du -h "$dump_file" | cut -f1)
    log "数据库导出完成: $dump_file ($local_size)"
}

# ── dump_minio ──
dump_minio() {
    local work_dir="$1"
    local minio_dir="${work_dir}/minio"
    mkdir -p "$minio_dir"

    log "导出 MinIO 对象存储..."

    check_container "$MINIO_CONTAINER"

    # 配置 mc alias
    docker exec "$MINIO_CONTAINER" mc alias set "$MINIO_ALIAS" \
        "http://localhost:9000" "$MINIO_USER" "$MINIO_PASS" >/dev/null 2>&1

    # 检查 bucket 是否存在
    if ! docker exec "$MINIO_CONTAINER" mc ls "${MINIO_ALIAS}/${MINIO_BUCKET}" >/dev/null 2>&1; then
        warn "MinIO bucket '${MINIO_BUCKET}' 不存在或为空"
        return 0
    fi

    # 统计对象数
    local obj_count
    obj_count=$(docker exec "$MINIO_CONTAINER" mc find "${MINIO_ALIAS}/${MINIO_BUCKET}" --older-than 0d 2>/dev/null | wc -l)
    local obj_size
    obj_size=$(docker exec "$MINIO_CONTAINER" mc du "${MINIO_ALIAS}/${MINIO_BUCKET}" --depth 1 2>/dev/null | tail -1 | awk '{print $1}')

    info "MinIO 对象数: $obj_count, 大小: ${obj_size:-未知}"

    if $DRY_RUN; then
        log "[DRY RUN] 将导出 MinIO bucket: $MINIO_BUCKET (${obj_count} objects)"
        return 0
    fi

    # Mirror 到容器内临时目录
    local tmp_dir="/tmp/minio_export_${TIMESTAMP}"
    docker exec "$MINIO_CONTAINER" mkdir -p "$tmp_dir"

    log "开始 mirror MinIO bucket (${obj_count} objects, 这可能需要几分钟)..."
    # mc mirror --quiet 仍输出文件列表到 stderr，全部重定向到 /dev/null
    # 仅保留真正的错误信息
    set +e
    local mc_stderr
    mc_stderr=$(docker exec "$MINIO_CONTAINER" mc mirror --quiet \
        "${MINIO_ALIAS}/${MINIO_BUCKET}" "$tmp_dir" 2>&1 >/dev/null)
    local mc_exit=$?
    set -e

    if [ "$mc_exit" -ne 0 ]; then
        err "mc mirror 失败 (exit code: $mc_exit)"
        [ -n "$mc_stderr" ] && warn "mc: $mc_stderr"
        docker exec "$MINIO_CONTAINER" rm -rf "$tmp_dir" 2>/dev/null || true
        return 1
    fi

    # 使用 docker cp 传输 (容器内不含 tar，无法 pipe)
    log "从容器传输 MinIO 数据 ($obj_count objects) ..."
    docker cp "${MINIO_CONTAINER}:${tmp_dir}/." "$minio_dir" 2>/dev/null

    local copied
    copied=$(find "$minio_dir" -type f 2>/dev/null | wc -l)
    if [ "$copied" -eq 0 ]; then
        err "MinIO 数据传输失败——未复制任何文件"
        return 1
    fi

    docker exec "$MINIO_CONTAINER" rm -rf "$tmp_dir" 2>/dev/null || true

    local local_size
    local_size=$(du -sh "$minio_dir" 2>/dev/null | cut -f1)
    log "MinIO 导出完成: $minio_dir ($local_size)"
}

# ── 主流程 ──
main() {
    echo ""
    echo "=========================================="
    echo "  SnapTrip 开发数据导出"
    echo "=========================================="
    echo ""

    # 创建临时工作目录
    local work_dir
    work_dir=$(mktemp -d -t snaptrip_dump_XXXXXX)
    trap 'rm -rf "${work_dir:-}"' EXIT

    local do_db=true
    local do_minio=true

    if $DB_ONLY; then
        do_minio=false
    elif $MINIO_ONLY; then
        do_db=false
    fi

    # 导出数据库
    if $do_db; then
        if ! dump_database "$work_dir"; then
            err "数据库导出失败"
            exit 1
        fi
    fi

    # 导出 MinIO
    if $do_minio; then
        if ! dump_minio "$work_dir"; then
            err "MinIO 导出失败"
            exit 1
        fi
    fi

    if $DRY_RUN; then
        log "[DRY RUN] 完成，未生成文件"
        exit 0
    fi

    # 打包为 tar.gz
    log "打包归档文件..."
    local output_dir
    output_dir="$(dirname "$OUTPUT_FILE")"
    mkdir -p "$output_dir"

    tar czf "$OUTPUT_FILE" -C "$work_dir" .

    local archive_size
    archive_size=$(du -h "$OUTPUT_FILE" | cut -f1)

    echo ""
    log "✅ 导出成功!"
    info "  文件: $OUTPUT_FILE"
    info "  大小: $archive_size"
    info ""
    info "  交给其他开发者后，执行:"
    info "    ./scripts/restore_dev_data.sh $OUTPUT_FILE"
    echo ""
}

main
