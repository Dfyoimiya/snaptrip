/**
 * ============================================
 * 购物车 API
 * 购物车增删改查等接口
 * ============================================
 */

import { get, post, put, del, patch } from '@/utils/request'
import type { CartItem } from '@/types/cart'

/**
 * 添加商品到购物车
 * @param data { product_id, sku_id, quantity }
 */
export const addCartAPI = (data: { product_id: string; sku_id: string; quantity: number }) => {
  return post<CartItem>('/api/v1/portal/cart', data)
}

/**
 * 获取购物车列表
 */
export const getCartListAPI = () => {
  return get<CartItem[]>('/api/v1/portal/cart')
}

/**
 * 删除购物车商品
 * @param id 购物车项ID
 */
export const deleteCartAPI = (id: string) => {
  return del(`/api/v1/portal/cart/${id}`)
}

/**
 * 更新购物车商品数量
 * @param id 购物车项ID
 * @param quantity 数量
 */
export const updateCartQuantityAPI = (id: string, quantity: number) => {
  return put<CartItem>(`/api/v1/portal/cart/${id}`, { quantity })
}

/**
 * 清空购物车
 */
export const clearCartAPI = () => {
  return del('/api/v1/portal/cart')
}

/**
 * 切换购物车项选中状态
 * @param id 购物车项ID
 * @param checked 选中状态 0或1
 */
export const toggleCartCheckedAPI = (id: string, checked: number) => {
  return patch<CartItem>(`/api/v1/portal/cart/${id}/checked?checked=${checked}`)
}
