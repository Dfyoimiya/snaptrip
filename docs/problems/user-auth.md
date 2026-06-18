# 用户/认证域问题清单

## 严重

### GAP-1: RBAC 权限守卫完全未启用
- **文件**: `backend/app/core/rbac.py:38-106` (定义), 所有 `backend/app/api/admin/*.py` (路由)
- **问题**: `require_admin_user`、`require_permissions`、`require_roles` 三个守卫函数完整实现了权限检查逻辑，但**没有任何管理后台路由使用它们**。所有管理后台路由仅依赖 `get_current_user`（仅校验 JWT+is_active）。
- **影响**: 任何已登录用户可访问全部管理功能：商品管理、订单管理、角色/权限分配、用户管理、仪表盘等。RBAC 模型（Role, Permission, UserRole, RoleMenu, RoleResource）完全成了摆设。

### GAP-2: 管理员注册端点无权限保护
- **文件**: `backend/app/api/admin/ums_admin.py:105-125`
- **问题**: `POST /api/v1/admin/register` 仅使用 `get_current_user`，任何认证用户可以注册新管理员账号。

## 高

### GAP-3: 无手机号注册/登录
- **文件**: `backend/marketplace/app/schemas/auth.py:12-14`, `backend/marketplace/app/models/users.py:27-44`
- **问题**: User 模型无 `phone_number` 字段。`RegisterRequest` 使用 `EmailStr`。注册仅支持邮箱+密码。
- **影响**: 无法使用手机号注册或登录，与中国市场用户习惯不符。

### GAP-4: 无短信验证
- **问题**: 项目中零短信发送/验证代码。无 SMS 服务对接。
- **影响**: 注册无手机验证、无短信通知、无营销短信。

### GAP-5: 无修改密码端点
- **问题**: 无 `PUT /password` 或类似端点供已登录用户修改密码。

### GAP-6: 无忘记密码/重置密码流程
- **问题**: 无密码重置 token 生成、无重置邮件/SMS 发送、无重置端点。

### GAP-7: 门户无个人信息修改端点
- **文件**: `backend/app/api/portal/member.py:26-29`
- **问题**: 门户仅有 `GET /portal/member/profile`，无 PUT/PATCH 端点。市场端 (`/api/v1/user/profile`) 有 PUT 但在不同路由前缀下。

## 中

### GAP-8: Access Token 登出后仍有效
- **文件**: `backend/marketplace/app/api/v1/auth.py:165-173`
- **问题**: 登出仅撤销 Refresh Token。Access Token（JWT 无状态）在过期前仍可访问受保护端点。无 JWT 黑名单机制。

### GAP-9: Portal 和 Admin 使用同一个 get_current_user
- **文件**: `backend/marketplace/app/core/security.py:68-116`
- **问题**: 门户路由和管理后台路由共用同一个认证依赖，无角色区分。唯一区分的 RBAC 层是死代码（见 GAP-1）。

## 低

### GAP-10: 无性别字段
- **文件**: `backend/marketplace/app/models/user_profile.py`
- **问题**: UserProfile 模型无 `gender` 字段。

### GAP-11: 无商家收藏
- **文件**: `backend/app/models/member/member.py:49-75`
- **问题**: 仅有 `UmsMemberFavorite` (商品收藏)，无商家收藏模型/端点。

### GAP-12: oauth_provider 字段存在但无 OAuth 流程
- **文件**: `backend/marketplace/app/models/users.py:39`
- **问题**: User 模型有 `oauth_provider` 列，但无 OAuth 登录端点/回调。
