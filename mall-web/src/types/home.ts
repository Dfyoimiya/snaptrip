/**
 * ============================================
 * 首页相关类型定义
 * 对应后端首页内容返回 Schema
 * ============================================
 */

import type { PmsBrand } from './brand'
import type { PmsProduct } from './product'

/** 专题信息 */
export interface CmsSubject {
  /** ID */
  id: string
  /** 分类ID */
  categoryId: string
  /** 专题分类名称 */
  categoryName: string
  /** 专题主图 */
  pic: string
  /** 画册图片用逗号分割 */
  albumPics: string
  /** 标题 */
  title: string
  /** 专题分类名称 */
  description: string
  /** 显示状态：0->不显示；1->显示 */
  showStatus: number
  /** 专题内容 */
  content: string
  /** 转发数 */
  forwardCount: number
  /** 收藏数 */
  collectCount: number
  /** 阅读数 */
  readCount: number
  /** 评论数 */
  commentCount: number
  /** 关联产品数量 */
  productCount: number
  /** 推荐状态 */
  recommendStatus: number
  /** 创建时间 */
  createdAt: string
}

/** 首页广告信息 */
export interface SmsHomeAdvertise {
  /** ID */
  id: string
  /** 名称 */
  name: string
  /** 广告图片 */
  pic: string
  /** 开始时间 */
  startTime: string
  /** 结束时间 */
  endTime: string
  /** 上线状态：0->关闭；1->开启 */
  status: number
  /** 点击数 */
  clickCount: number
  /** 下单数 */
  orderCount: number
  /** 链接地址 */
  url: string
  /** 备注 */
  note: string
  /** 排序 */
  sort: number
  /** 创建时间 */
  createdAt: string
}

/** 首页秒杀信息 */
export interface HomeFlashPromotion {
  /** 开始时间 */
  startTime: string
  /** 结束时间 */
  endTime: string
  /** 下场开始时间 */
  nextStartTime: string
  /** 下场结束时间 */
  nextEndTime: string
  /** 商品列表 */
  productList: PmsProduct[]
}

/** 首页内容返回结果 */
export interface HomeContentResult {
  /** 轮播横幅列表 */
  banners: SmsHomeAdvertise[]
  /** 新品推荐商品 */
  newProducts: PmsProduct[]
  /** 人气推荐商品 */
  recommendProducts: PmsProduct[]
  /** 推荐专题列表 */
  subjects: CmsSubject[]
}
