/**
 * 首页专题
 */
export interface CmsSubject {
  id?: number
  categoryId?: number
  title?: string
  pic?: string
  productCount?: number
  recommendStatus?: number // 0->不推荐 1->推荐
  createTime?: string
  collectCount?: number
  readCount?: number
  commentCount?: number
  albumPics?: string
  description?: string
  showStatus?: number // 0->不展示 1->展示
  forwardCount?: number
  categoryName?: string // 分类名称（用于展示）
}

/**
 * 专题分类
 */
export interface CmsSubjectCategory {
  id?: number
  name?: string
  icon?: string
  subjectCount?: number
  showStatus?: number
  sort?: number
  createTime?: string
}
