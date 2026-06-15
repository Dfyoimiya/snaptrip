/** 订单 */
export interface OmsOrder {
  id?: string
  userId?: string
  orderSn?: string
  createdAt?: string
  memberUsername?: string
  totalAmount?: number
  payAmount?: number
  freightAmount?: number
  discountAmount?: number
  payType?: number
  status?: number
  deliveryCompany?: string
  deliverySn?: string
  receiverName?: string
  receiverPhone?: string
  receiverPostCode?: string
  receiverProvince?: string
  receiverCity?: string
  receiverRegion?: string
  receiverDetailAddress?: string
  note?: string
  paymentTime?: string
  deliveryTime?: string
  receiveTime?: string
  updatedAt?: string
}

/** 订单详情（含商品、操作记录） */
export interface OmsOrderDetail extends OmsOrder {
  items?: OmsOrderItem[]
  historyList?: OmsOrderOperateHistory[]
}

/** 订单商品 */
export interface OmsOrderItem {
  id?: string
  orderId?: string
  orderSn?: string
  productId?: string
  productPic?: string
  productName?: string
  productBrand?: string
  productSn?: string
  price?: number
  quantity?: number
  skuId?: string
  skuCode?: string
  categoryId?: string
  promotionAmount?: number
  couponAmount?: number
  integrationAmount?: number
  realAmount?: number
  spec?: string
}

/** 订单操作记录 */
export interface OmsOrderOperateHistory {
  id?: string
  orderId?: string
  operateMan?: string
  createdAt?: string
  orderStatus?: number
  note?: string
}

/** 订单发货参数 */
export interface OmsOrderDeliveryParam {
  orderId: string
  deliveryCompany: string
  deliverySn: string
}

/** 收货人信息参数 */
export interface OmsReceiverInfoParam {
  orderId: string
  receiverName?: string
  receiverPhone?: string
  receiverPostCode?: string
  receiverProvince?: string
  receiverCity?: string
  receiverRegion?: string
  receiverDetailAddress?: string
  status?: number
}

/** 订单费用参数 */
export interface OmsMoneyInfoParam {
  orderId: string
  freightAmount?: number
  discountAmount?: number
  status?: number
}

/** 订单备注参数 */
export interface OmsOrderNoteParam {
  id: string
  note: string
  status: number
}

/** 订单查询参数 */
export interface OrderQueryParam {
  orderSn?: string
  receiverKeyword?: string
  status?: number
  orderType?: number
  sourceType?: number
  createdAt?: string
  page: number
  page_size: number
}
