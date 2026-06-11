/**
 * ============================================
 * 品牌相关类型定义
 * 对应后端 PmsBrand Schema
 * ============================================
 */

/** 品牌信息 */
export interface PmsBrand {
  /** 品牌ID */
  id: number
  /** 品牌名称 */
  name: string
  /** 首字母 */
  firstLetter: string
  /** 品牌logo */
  logo: string
  /** 专区大图 */
  bigPic: string
  /** 品牌故事 */
  brandStory: string
  /** 排序 */
  sort: number
  /** 是否显示：0->不显示；1->显示 */
  showStatus: number
  /** 产品数量 */
  productCount: number
  /** 产品评论数量 */
  productCommentCount: number
  /** 品牌logo（用于前端展示） */
  pic?: string
  /** 创建时间 */
  createTime: string
}
