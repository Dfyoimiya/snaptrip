"""
【CMS 内容模型】— cms_banners / cms_subjects / cms_helps 表

知识点速查：
  - Banner vs Subject: Banner=首页轮播(运营位), Subject=内容专题页(如"618攻略")
  - 为什么 Banner 不用 JSON 存 product_id 列表？
    如果 Banner 需要跳转到具体商品，应建 cms_banner_products 中间表
    当前简化设计: url 字段存跳转链接，支持商品详情页或外部链接

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class CmsBanner(CommerceBase, AuditMixin):
    """
    首页轮播图 —— 位置、图片、跳转链接。
    """

    __tablename__ = "cms_banners"

    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="轮播图标题")
    pic: Mapped[str] = mapped_column(String(255), nullable=False, comment="图片URL")
    url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="跳转链接")
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序(越小越前)")
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="0=禁用 1=启用")
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="上线时间")
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="下线时间")


class CmsSubject(CommerceBase, AuditMixin):
    """
    专题内容 —— 如"新品首发"、"618省钱攻略"。
    """

    __tablename__ = "cms_subjects"

    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="专题标题")
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="摘要")
    pic: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="封面图")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="内容(富文本HTML)")
    category_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="分类名称")
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="0=禁用 1=启用")
    recommend_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="0=否 1=推荐")


class CmsHelp(CommerceBase, AuditMixin):
    """
    帮助中心。
    """

    __tablename__ = "cms_helps"

    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="帮助标题")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="帮助内容(富文本HTML)")
    category_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="分类: 购物指南/售后/配送")
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="0=禁用 1=启用")
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")
