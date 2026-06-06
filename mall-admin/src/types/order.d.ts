/** 订单 */
export interface OmsOrder {
  id?: number
  memberId?: number
  couponId?: number
  orderSn?: string
  createTime?: string
  memberUsername?: string
  totalAmount?: number
  payAmount?: number
  freightAmount?: number
  promotionAmount?: number
  integrationAmount?: number
  couponAmount?: number
  discountAmount?: number
  payType?: number
  sourceType?: number
  status?: number
  orderType?: number
  deliveryCompany?: string
  deliverySn?: string
  autoConfirmDay?: number
  integration?: number
  growth?: number
  promotionInfo?: string
  billType?: number
  billHeader?: string
  billContent?: string
  billReceiverPhone?: string
  billReceiverEmail?: string
  receiverName?: string
  receiverPhone?: string
  receiverPostCode?: string
  receiverProvince?: string
  receiverCity?: string
  receiverRegion?: string
  receiverDetailAddress?: string
  note?: string
  confirmStatus?: number
  deleteStatus?: number
  useIntegration?: number
  paymentTime?: string
  deliveryTime?: string
  receiveTime?: string
  commentTime?: string
  modifyTime?: string
}

/** 订单详情（含商品、操作记录） */
export interface OmsOrderDetail extends OmsOrder {
  orderItemList?: OmsOrderItem[]
  historyList?: OmsOrderOperateHistory[]
}

/** 订单商品 */
export interface OmsOrderItem {
  id?: number
  orderId?: number
  orderSn?: string
  productId?: number
  productPic?: string
  productName?: string
  productBrand?: string
  productSn?: string
  productPrice?: number
  productQuantity?: number
  productSkuId?: number
  productSkuCode?: string
  productCategoryId?: number
  promotionAmount?: number
  couponAmount?: number
  integrationAmount?: number
  realAmount?: number
  giftIntegration?: number
  giftGrowth?: number
  productAttr?: string[]
}

/** 订单操作记录 */
export interface OmsOrderOperateHistory {
  id?: number
  orderId?: number
  operateMan?: string
  createTime?: string
  orderStatus?: number
  note?: string
}

/** 订单发货参数 */
export interface OmsOrderDeliveryParam {
  orderId: number
  deliveryCompany: string
  deliverySn: string
}

/** 收货人信息参数 */
export interface OmsReceiverInfoParam {
  orderId: number
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
  orderId: number
  freightAmount?: number
  discountAmount?: number
  status?: number
}

/** 订单备注参数 */
export interface OmsOrderNoteParam {
  id: number
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
  createTime?: string
  pageNum: number
  pageSize: number
}
