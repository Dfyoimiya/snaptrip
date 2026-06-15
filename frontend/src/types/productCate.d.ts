/** 商品分类 */
export interface PmsProductCategory {
  id?: string
  parentId: string
  name: string
  level?: number
  productCount?: number
  productUnit: string
  navStatus?: number
  showStatus?: number
  sort?: number
  icon?: string
  keywords?: string
  description?: string
  children?: PmsProductCategory[]
}
