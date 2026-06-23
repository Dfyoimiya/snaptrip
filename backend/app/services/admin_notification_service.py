"""B 端业务通知服务。"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import distinct, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import ADMIN_ROLE_PREFIXES, ADMIN_ROLE_SUFFIXES, SUPER_ADMIN_ROLES
from app.models.infra.notification import CsNotification
from app.models.rbac import Role, UserRole
from app.schemas.admin_notification import AdminNotificationCreate
from app.schemas.cs_admin import NotificationResponse
from app.utils.redis_pubsub import publish_admin_notification
from marketplace.app.models.users import User

logger = logging.getLogger(__name__)


class AdminNotificationService:
    """将 C 端业务事件通知给所有启用的 B 端角色用户。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def notify_admins(self, data: AdminNotificationCreate) -> list[CsNotification]:
        recipient_result = await self.db.execute(
            select(distinct(UserRole.user_id))
            .join(Role, Role.id == UserRole.role_id)
            .join(User, User.id == UserRole.user_id)
            .where(
                Role.status == 1,
                User.is_active.is_(True),
                or_(
                    Role.name.in_(SUPER_ADMIN_ROLES),
                    *(Role.name.startswith(prefix) for prefix in ADMIN_ROLE_PREFIXES),
                    *(Role.name.endswith(suffix) for suffix in ADMIN_ROLE_SUFFIXES),
                ),
            )
        )
        recipient_ids = list(recipient_result.scalars().all())
        if not recipient_ids:
            logger.info("admin_notification_skipped no_active_admin type=%s", data.type)
            return []

        notifications = [
            CsNotification(
                recipient_id=recipient_id,
                type=data.type,
                ticket_id=data.ticket_id,
                title=data.title,
                body=data.body,
                action_url=data.action_url,
            )
            for recipient_id in recipient_ids
        ]
        self.db.add_all(notifications)
        await self.db.commit()

        for notification in notifications:
            await self.db.refresh(notification)

        for notification in notifications:
            payload = NotificationResponse.model_validate(notification).model_dump(mode="json")
            asyncio.create_task(publish_admin_notification(str(notification.recipient_id), payload))

        logger.info(
            "admin_notification_created type=%s recipients=%s",
            data.type,
            len(notifications),
        )
        return notifications
