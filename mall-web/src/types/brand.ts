/**
 * ============================================
 * 品牌相关类型定义
 * 对应后端 PmsBrand Schema
 * ============================================
 */

/** 品牌信息 */
export interface PmsBrand {
  /** 品牌ID */
  id: string
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
  /** 创建时间 */
  createdAt: string
  /** 商品数量（列表接口可能返回） */
  productCount?: number
}
