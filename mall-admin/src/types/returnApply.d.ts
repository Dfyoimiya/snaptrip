/** 退货申请 */
export interface OmsOrderReturnApply {
  id?: number
  orderId?: number
  productId?: number
  orderSn?: string
  createTime?: string
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
  companyAddressId?: number
}

/** 退货申请查询参数 */
export interface ReturnApplyQueryParam {
  id?: number
  status?: number
  createTime?: string
  handleMan?: string
  handleTime?: string
  pageNum: number
  pageSize: number
}

/** 更新退货申请状态参数 */
export interface OmsUpdateStatusParam {
  id: number
  companyAddressId: number
  handleMan: string
  handleNote: string
  receiveMan: string
  receiveNote: string
  returnAmount: number
  status: number
}
