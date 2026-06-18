/**
 * ============================================
 * 订单相关类型定义
 * 对应后端 OmsOrder 及其关联 Schema
 * ============================================
 */

import type { MemberReceiveAddress } from './address'
import type { SmsCoupon } from './coupon'

/** 购物车促销项 */
export interface CartPromotionItem {
  /** ID */
  id: number
  /** 商品ID */
  productId: number
  /** 商品名称 */
  productName: string
  /** 商品主图 */
  productPic: string
  /** 商品销售属性 JSON 字符串 */
  productAttr: string
  /** 商品SKU条码 */
  skuCode: string
  /** 商品SKU ID */
  skuId: number
  /** 商品副标题（卖点） */
  productSubTitle: string
  /** 促销活动信息 */
  promotionMessage: string
  /** 商品价格 */
  price: number
  /** 购买数量 */
  quantity: number
  /** 促销活动减去的金额 */
  reduceAmount: number
  /** 剩余库存-锁定库存 */
  realStock: number
  /** 会员昵称 */
  memberNickname: string
  /** 创建时间 */
  createDate: string
}

/** 计算金额 */
export interface CalcAmount {
  /** 商品合计金额 */
  totalAmount: number
  /** 运费 */
  freightAmount: number
  /** 应付金额 */
  payAmount: number
}

/** 积分消费设置 */
export interface UmsIntegrationConsumeSetting {
  /** ID */
  id: number
  /** 是否可以和优惠券同用；0->不可以；1->可以 */
  couponStatus: number
  /** 每一元需要抵扣的积分数量 */
  deductionPerAmount: number
  /** 每笔订单最高抵用百分比 */
  maxPercentPerOrder: number
  /** 每次使用积分最小单位100 */
  useUnit: number
}

/** 优惠券历史详情 */
export interface SmsCouponHistoryDetail {
  /** ID */
  id: number
  /** 优惠券ID */
  couponId: number
  /** 优惠券码 */
  couponCode: string
  /** 会员昵称 */
  memberNickname: string
  /** 优惠券信息 */
  coupon: SmsCoupon
  /** 获取类型：0->后台赠送；1->主动获取 */
  getType: number
  /** 使用状态：0->未使用；1->已使用；2->已过期 */
  useStatus: number
  /** 使用时间 */
  useTime: string
  /** 创建时间 */
  createdAt: string
  /** 订单编号 */
  orderId: number
}

/** 确认订单返回结果 */
export interface ConfirmOrderResult {
  /** 收货地址列表 */
  memberReceiveAddressList: MemberReceiveAddress[]
  /** 购物车促销商品列表 */
  cartPromotionItemList: CartPromotionItem[]
  /** 用户可用优惠券列表 */
  couponHistoryDetailList: SmsCouponHistoryDetail[]
  /** 计算金额 */
  calcAmount: CalcAmount
  /** 积分消费设置 */
  integrationConsumeSetting: UmsIntegrationConsumeSetting
  /** 会员持有的积分 */
  memberIntegration: number
}

/** 创建订单请求参数（对应API文档 OrderParam） */
export interface OrderParam {
  cart_item_ids: string[]
  receiver_name: string
  receiver_phone: string
  receiver_province?: string
  receiver_city?: string
  receiver_region?: string
  receiver_detail_address: string
  receiver_post_code?: string
  note?: string
  pay_type: number
  coupon_id?: string | null
}

/** 生成订单返回结果（对应后端 OrderResult） */
export type GenerateOrderResult = OmsOrderDetail

/** 订单商品项 */
export interface OmsOrderItem {
  /** ID */
  id: string
  /** 订单ID */
  orderId?: string
  /** 商品ID */
  productId: string
  /** 商品名称 */
  productName: string
  /** 商品主图 */
  productPic: string
  /** 商品规格描述 JSON 字符串 */
  spec: string
  /** 商品SKU ID */
  skuId: string
  /** 商品SKU条码 */
  skuCode: string
  /** 销售价格 */
  price: number
  /** 购买数量 */
  quantity: number
}

/** 订单详情（对应API文档 OmsOrderDetail） */
export interface OmsOrderDetail {
  /** 订单ID */
  id: string
  /** 订单编号 */
  orderSn: string
  /** 用户帐号 */
  memberUsername: string
  /** 订单总金额 */
  totalAmount: number
  /** 运费金额 */
  freightAmount: number
  /** 应付金额 */
  payAmount: number
  /** 支付方式：0->未支付；1->支付宝；2->微信 */
  payType: number
  /** 订单状态：0->待付款；1->待发货；2->已发货；3->已完成；4->已关闭；5->无效订单 */
  status: number
  /** 优惠券ID */
  couponId?: string | null
  /** 订单备注 */
  note?: string | null
  /** 提交时间 */
  createdAt: string
  /** 支付时间 */
  paymentTime?: string | null
  /** 发货时间 */
  deliveryTime?: string | null
  /** 收货人姓名 */
  receiverName: string
  /** 收货人电话 */
  receiverPhone: string
  /** 省份/直辖市 */
  receiverProvince: string
  /** 城市 */
  receiverCity: string
  /** 区 */
  receiverRegion: string
  /** 详细地址 */
  receiverDetailAddress: string
  /** 收货人邮编 */
  receiverPostCode?: string | null
  /** 物流公司 */
  deliveryCompany?: string | null
  /** 物流单号 */
  deliverySn?: string | null
  /** 管理员后台调整订单使用的折扣金额 */
  discountAmount: number
  /** 订单商品列表 */
  items: OmsOrderItem[]
}

/** 退货申请请求参数 */
export interface OmsOrderReturnApplyParam {
  /** 订单ID */
  orderId: number
  /** 订单编号 */
  orderSn: string
  /** 会员用户名 */
  memberUsername: string
  /** 退货商品ID */
  productId: number
  /** 商品名称 */
  productName: string
  /** 商品图片 */
  productPic: string
  /** 商品销售属性 */
  productAttr: string
  /** 商品品牌 */
  productBrand: string
  /** 商品单价 */
  productPrice: number
  /** 商品实际支付单价 */
  productRealPrice: number
  /** 退货数量 */
  productCount: number
  /** 原因 */
  reason: string
  /** 描述 */
  description: string
  /** 凭证图片，以逗号隔开 */
  proofPics: string
  /** 退货人姓名 */
  returnName: string
  /** 退货人电话 */
  returnPhone: string
}
