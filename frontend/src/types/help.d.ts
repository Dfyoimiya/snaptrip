/**
 * 帮助中心
 */
export interface CmsHelp {
  id?: number
  title?: string
  content?: string
  categoryName?: string
  status?: number    // 0->不展示 1->展示
  sort?: number
  createdAt?: string
}
