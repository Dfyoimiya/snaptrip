# 契约层问题

> **已于 2026-06-18 删除。** `contracts/` 目录已从代码库移除（commit `f593cfd`）。

## 背景

`contracts/` 是一个独立 Python 包，定义了：

- **17 个 Protocol 端口** (2 个文件)
  - `repositories.py`: 13 个 Repository Protocol (UserRepoPort, ProductRepoPort, OrderRepoPort 等)
  - `external_services.py`: 4 个外部服务 Protocol (GeoPort, PaymentPort, NotificationPort, StoragePort)
- **11 个 Schema 模块** (11 个文件): common, enums, errors, user/auth, product, order, search, admin, marketing, payment, merchant

## 问题

| # | 问题 | 详情 |
|---|------|------|
| 1 | 零导入 | `backend/`、`agent/`、`shared/` 均无 `from contracts` 导入 |
| 2 | 不在 workspace | 根 `pyproject.toml` members 不含 `contracts`，`uv sync` 不安装 |
| 3 | 17 端口零实现 | 无任何类实现这些 Protocol，后端直接用 SQLAlchemy |
| 4 | Schema 体系完全分离 | 合同 Schema 与 `backend/app/schemas/` 是两套独立体系： |
|   | - 类型不兼容 | 合同用 `str` ID / `int` 价格，后端用 `UUID` / `Decimal` |
|   | - 状态机不同 | 合同 OrderStatus 6 状态 (str Enum)，后端 8 状态 (int 常量) |
|   | - 字段命名不同 | `size` vs `page_size`，`list` vs `items`，`contact_name` vs `name` |
|   | - 错误码系统不同 | 合同 IntEnum 错误码 vs 后端 str code exception |
|   | - 响应信封不同 | 合同 `Result[T]` 含 `timestamp`，后端 `success()` 无时间戳 |

## 结论

`contracts/` 是项目早期的"目标架构"设计草案，从未被后续开发采用，属死代码，已删除。
