/** 商品分类 */
export interface PmsProductCategory {
  id?: number
  parentId: number
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
