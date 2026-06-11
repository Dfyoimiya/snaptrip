/**
 * ============================================
 * 收货地址 API
 * 地址的增删改查等接口
 * ============================================
 */

import { get, post } from '@/utils/request'
import type { MemberReceiveAddress } from '@/types/address'

/**
 * 获取会员收货地址列表
 */
export const getAddressListAPI = () => {
  return get<MemberReceiveAddress[]>('/member/address/list')
}

/**
 * 根据ID获取收货地址详情
 * @param id 地址ID
 */
export const getAddressDetailAPI = (id: number) => {
  return get<MemberReceiveAddress>(`/member/address/${id}`)
}

/**
 * 添加收货地址
 * @param data 地址信息
 */
export const addAddressAPI = (data: MemberReceiveAddress) => {
  return post<unknown>('/member/address/add', data)
}

/**
 * 修改收货地址
 * @param id 地址ID
 * @param data 地址信息
 */
export const updateAddressAPI = (id: number, data: MemberReceiveAddress) => {
  return post<unknown>(`/member/address/update/${id}`, data)
}

/**
 * 删除收货地址
 * @param id 地址ID
 */
export const deleteAddressAPI = (id: number) => {
  return post<unknown>(`/member/address/delete/${id}`)
}

/**
 * 设置默认收货地址
 * @param id 地址ID
 */
export const setDefaultAddressAPI = (id: number) => {
  return post<unknown>(`/member/address/setDefault/${id}`)
}
