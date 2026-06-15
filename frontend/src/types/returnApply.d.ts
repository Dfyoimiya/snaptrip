/** 退货申请 */
export interface OmsOrderReturnApply {
  id?: string
  orderId?: string
  productId?: string
  orderSn?: string
  createdAt?: string
  memberUsername?: string
  returnAmount?: number
  returnName?: string
  returnPhone?: string
  status?: number
  handleTime?: string
  productPic?: string
  productName?: string
  productBrand?: string
  productAttr?: string
  productCount?: number
  productRealPrice?: number
  reason?: string
  description?: string
  proofPics?: string
  handleNote?: string
  handleMan?: string
  receiveMan?: string
  receiveTime?: string
  receiveNote?: string
  companyAddressId?: string
}

/** 退货申请查询参数 */
export interface ReturnApplyQueryParam {
  id?: string
  status?: number
  createdAt?: string
  handleMan?: string
  handleTime?: string
  page: number
  page_size: number
}

/** 更新退货申请状态参数 */
export interface OmsUpdateStatusParam {
  id: string
  companyAddressId: string
  handleMan: string
  handleNote: string
  receiveMan: string
  receiveNote: string
  returnAmount: number
  status: number
}
