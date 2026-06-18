"""SMS 验证码服务 —— 基于 Redis 的验证码存储与校验。

当前为 Mock 实现（不接入真实 SMS 网关），验证码通过日志打印，存储在 Redis 中，
TTL 为 5 分钟。

Usage:
    from app.services.sms_service import sms_service
    await sms_service.send_sms("13800138000", "register")
    await sms_service.verify_sms("13800138000", "123456", "register")

Author: SnapTrip Team
Date: 2026-06-18
"""

from __future__ import annotations

import logging
import secrets

from snaptrip_shared.db.redis import get_redis_client

_logger = logging.getLogger(__name__)

# 验证码有效期 5 分钟
_CODE_TTL_SECONDS = 300
# Redis key 前缀
_KEY_PREFIX = "sms:code"


class SmsService:
    """SMS 验证码服务（Mock 实现）。"""

    @staticmethod
    def _redis_key(phone: str, scene: str) -> str:
        """生成 Redis 存储键。"""
        return f"{_KEY_PREFIX}:{scene}:{phone}"

    @staticmethod
    def _generate_code() -> str:
        """生成 6 位随机数字验证码。"""
        return f"{secrets.randbelow(1_000_000):06d}"

    async def send_sms(self, phone: str, scene: str) -> bool:
        """发送短信验证码到指定手机号。

        Args:
            phone: 手机号码。
            scene: 业务场景（如 "register", "login", "reset_password"）。

        Returns:
            True 表示发送成功（Mock 实现始终返回 True）。
        """
        code = self._generate_code()
        key = self._redis_key(phone, scene)

        try:
            redis = await get_redis_client()
            await redis.set(key, code, ex=_CODE_TTL_SECONDS)
            await redis.close()
        except Exception:
            _logger.exception("Redis 存储验证码失败, phone=%s, scene=%s", phone, scene)
            return False

        # Mock 实现：验证码打印到控制台
        _logger.info(
            "【Mock SMS】向 %s 发送验证码: %s (场景: %s, 有效期: %d秒)",
            phone,
            code,
            scene,
            _CODE_TTL_SECONDS,
        )
        return True

    async def verify_sms(self, phone: str, code: str, scene: str) -> bool:
        """验证短信验证码。

        Args:
            phone: 手机号码。
            code: 用户输入的验证码。
            scene: 业务场景。

        Returns:
            True 表示验证码正确，False 表示验证码错误或已过期。
        """
        key = self._redis_key(phone, scene)

        try:
            redis = await get_redis_client()
            stored = await redis.get(key)
            if stored is not None:
                # 验证成功后删除验证码（一次性使用）
                await redis.delete(key)
            await redis.close()
        except Exception:
            _logger.exception("Redis 校验验证码失败, phone=%s, scene=%s", phone, scene)
            return False

        if stored is None:
            _logger.info("验证码不存在或已过期, phone=%s, scene=%s", phone, scene)
            return False

        stored_str = stored.decode("utf-8") if isinstance(stored, bytes) else stored
        if stored_str != code:
            _logger.info("验证码不匹配, phone=%s, scene=%s", phone, scene)
            return False

        _logger.info("验证码校验成功, phone=%s, scene=%s", phone, scene)
        return True


sms_service = SmsService()
