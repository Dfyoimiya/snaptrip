/**
 * ============================================
 * 购物车 API
 * 购物车增删改查等接口
 * ============================================
 */

import { get, post } from '@/utils/request'
import type { CartItem } from '@/types/cart'

/**
 * 添加商品到购物车
 * @param data 购物车项数据
 */
export const addCartAPI = (data: Partial<CartItem>) => {
  return post<unknown>('/cart/add', data)
}

/**
 * 获取购物车列表
 */
export const getCartListAPI = () => {
  return get<CartItem[]>('/cart/list')
}

/**
 * 删除购物车商品
 * @param ids 购物车项ID，多个用逗号分隔
 */
export const deleteCartAPI = (ids: string) => {
  return post<unknown>('/cart/delete', null, { params: { ids } })
}

/**
 * 更新购物车商品数量
 * @param id 购物车项ID
 * @param quantity 数量
 */
export const updateCartQuantityAPI = (id: string, quantity: number) => {
  return get<unknown>('/cart/update/quantity', { id, quantity })
}

/**
 * 清空购物车
 */
export const clearCartAPI = () => {
  return post<unknown>('/cart/clear')
}
