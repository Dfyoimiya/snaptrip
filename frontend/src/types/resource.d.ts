/** 资源分类 */
export interface UmsResourceCategory {
  id?: string
  name?: string
  sort?: number
  createTime?: string
}

/** 资源 */
export interface UmsResource {
  id?: string
  categoryId?: number
  name?: string
  url?: string
  description?: string
  createTime?: string
}
