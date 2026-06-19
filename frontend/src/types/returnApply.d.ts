/** 退货申请（后端 snake_case 经响应拦截器转 camelCase） */
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
  companyAddressId?: number
}

/** 退货申请查询参数（发送给后端，使用 snake_case） */
export interface ReturnApplyQueryParam {
  id?: string
  status?: number
  create_time?: string
  handle_man?: string
  handle_time?: string
  page: number
  page_size: number
}

/** 更新退货申请状态参数（匹配后端 ReturnApplyUpdateStatus） */
export interface ReturnApplyUpdateStatusParam {
  status: number
  handle_note?: string
  handle_man?: string
  receive_man?: string
  receive_note?: string
  return_amount?: number
  company_address_id?: number
}
