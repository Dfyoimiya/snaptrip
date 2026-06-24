/** 商品分类 */
export interface PmsProductCategory {
  id?: string
  parentId: string | number | null
  name: string
  type?: 'PRODUCT' | 'COMBO'
  level?: number
  productCount?: number
  productUnit?: string
  navStatus?: number
  showStatus?: number
  sort?: number
  icon?: string
  keywords?: string
  description?: string
  children?: PmsProductCategory[]
}
