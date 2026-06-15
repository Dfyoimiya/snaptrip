/**
 * ============================================
 * 购物车相关类型定义
 * 对应后端 CartItemResponse Schema
 * ============================================
 */

/** 购物车项 */
export interface CartItem {
  /** 购物车项 ID */
  id: string
  /** 商品 ID */
  productId: string
  /** 商品 SKU ID */
  skuId: string
  /** 商品 SKU 编码 */
  skuCode: string
  /** 规格描述 */
  spec: string
  /** 商品名称 */
  productName: string
  /** 商品主图 */
  productPic: string
  /** 商品价格 */
  price: number
  /** 商品原价/划线价 */
  originalPrice?: number
  /** 商品数量 */
  quantity: number
  /** 前端扩展字段：选中状态 */
  checked?: boolean
}
