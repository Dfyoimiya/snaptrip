/**
 * ============================================
 * 收货地址 API
 * 地址的增删改查等接口
 * ============================================
 */

import { get, post, put, del } from '@/utils/request'
import type { MemberReceiveAddress } from '@/types/address'

/**
 * 获取会员收货地址列表
 */
export const getAddressListAPI = () => {
  return get<MemberReceiveAddress[]>('/api/v1/portal/member/addresses')
}

/**
 * 添加收货地址
 * @param data 地址信息
 */
export const addAddressAPI = (data: Partial<MemberReceiveAddress>) => {
  return post<MemberReceiveAddress>('/api/v1/portal/member/addresses', data)
}

/**
 * 修改收货地址
 * @param id 地址ID
 * @param data 地址信息
 */
export const updateAddressAPI = (id: string, data: Partial<MemberReceiveAddress>) => {
  return put<MemberReceiveAddress>(`/api/v1/portal/member/addresses/${id}`, data)
}

/**
 * 删除收货地址
 * @param id 地址ID
 */
export const deleteAddressAPI = (id: string) => {
  return del(`/api/v1/portal/member/addresses/${id}`)
}

/**
 * 根据ID获取收货地址详情（从列表中查找）
 */
export const getAddressDetailAPI = async (id: string): Promise<MemberReceiveAddress | null> => {
  const list = await getAddressListAPI()
  return list.find((a) => String(a.id) === id) || null
}

/**
 * 设置默认收货地址
 * @param id 地址ID
 */
export const setDefaultAddressAPI = (id: string) => {
  return put<MemberReceiveAddress>(`/api/v1/portal/member/addresses/${id}`, { default_status: 1 })
}
