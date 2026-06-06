/** 商品分类对应属性信息 */
export interface ProductAttrInfo {
  attributeId: number
  attributeCategoryId: number
}

/** 商品属性分类 */
export interface PmsProductAttributeCategory {
  id?: number
  name: string
  attributeCount?: number
  paramCount?: number
}

/** 商品属性分类扩展（含属性列表） */
export interface PmsProductAttributeCategoryExt extends PmsProductAttributeCategory {
  productAttributeList?: PmsProductAttribute[]
}

/** 商品属性 */
export interface PmsProductAttribute {
  id?: number
  productAttributeCategoryId: number
  name: string
  selectType?: number
  inputType?: number
  inputList?: string
  sort?: number
  type?: number
  handAddStatus?: number
  searchType?: number
  relatedStatus?: number
}
