/** 资源分类 */
export interface UmsResourceCategory {
  id?: string
  name?: string
  sort?: number
  createdAt?: string
}

/** 资源 */
export interface UmsResource {
  id?: string
  categoryId?: string
  name?: string
  url?: string
  description?: string
  createdAt?: string
}
