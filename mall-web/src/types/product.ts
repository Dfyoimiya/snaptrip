/**
 * ============================================
 * 商品相关类型定义
 * 对应后端 PmsProduct 及其关联 Schema
 *
 * NOTE: Field names match the backend snake_case response after the
 * request interceptor converts keys to camelCase.
 * ============================================
 */

import type { PageParam } from './common'

/** 商品信息（列表项 —— 匹配 portal/products 返回字段） */
export interface PmsProduct {
  /** 商品ID */
  id: string
  /** 商品名称 */
  name: string
  /** 副标题 */
  subTitle?: string | null
  /** 品牌ID */
  brandId?: string | null
  /** 品牌名称（详情接口填充，列表可能缺失） */
  brandName?: string | null
  /** 分类ID */
  categoryId?: string | null
  /** 分类名称（详情接口填充，列表可能缺失） */
  productCategoryName?: string | null
  /** 主图 */
  defaultPic?: string | null
  /** 画册图片（逗号分隔） */
  albumPics?: string | null
  /** 货号 */
  productSn?: string | null
  /** 价格 */
  price: number
  /** 原价/划线价 */
  originalPrice?: number | null
  /** 促销价格 */
  promotionPrice?: number | null
  /** 促销开始时间 */
  promotionStartTime?: string | null
  /** 促销结束时间 */
  promotionEndTime?: string | null
  /** 每人限购数 */
  promotionPerLimit?: number
  /** 促销类型：0->无促销；1->单品优惠；2->会员优惠；3->多买优惠；4->满减优惠；5->限时优惠 */
  promotionType?: number
  /** 新品状态：0->非新品；1->新品 */
  newStatus?: number
  /** 推荐状态：0->不推荐；1->推荐 */
  recommendStatus?: number
  /** 库存 */
  stock: number
  /** 销量 */
  saleCount?: number
  /** 多图（JSON 数组字符串） */
  pics?: string | null
  /** 详情描述 HTML */
  description?: string | null
  /** 关键词 */
  keywords?: string | null
  /** 单位 */
  unit?: string | null
  /** 重量 */
  weight?: string | null
  /** 服务 ID 列表（逗号分隔） */
  serviceIds?: string | null
  /** 运费模板 ID */
  freightTemplateId?: string | null
  /** 创建时间 */
  createdAt?: string | null
  /** 更新时间 */
  updatedAt?: string | null
}

/** 商品分类信息 - 对应后端 PmsProductCategory Schema */
export interface PmsProductCategory {
  /** ID */
  id: string
  /** 上级分类ID */
  parentId: string | null
  /** 分类名称 */
  name: string
  /** 分类级别：0->1级；1->2级 */
  level: number
  /** 排序 */
  sort: number
  /** 图标 */
  icon?: string | null
  /** 商品数量 */
  productCount?: number
  /** 商品单位 */
  productUnit?: string | null
  /** 是否显示在导航栏：0->不显示；1->显示 */
  navStatus: number
  /** 显示状态：0->不显示；1->显示 */
  showStatus: number
  /** 描述 */
  description?: string | null
  /** 关键字 */
  keywords?: string | null
  /** 创建时间 */
  createdAt?: string | null
}

/** 商品分类树节点 */
export interface CategoryTreeNode {
  /** 分类ID */
  id: string
  /** 分类名称 */
  name: string
  /** 子分类列表 */
  children?: CategoryTreeNode[]
}

/** 商品列表搜索请求参数 */
export interface ProductListParam extends PageParam {
  /** 搜索关键字 */
  keyword?: string
  /** 商品分类ID */
  productCategoryId?: string
  /** 品牌ID */
  brandId?: string
  /** 排序方式：0->综合排序；1->新品；2->销量；3->价格从低到高；4->价格从高到低 */
  sort: number
  /** 最低价格 */
  minPrice?: number
  /** 最高价格 */
  maxPrice?: number
}

/** 商品属性 - 对应后端 PmsProductAttribute Schema */
export interface PmsProductAttribute {
  /** 属性ID */
  id: string
  /** 属性名称 */
  name: string
  /** 属性的类型；0->规格；1->参数 */
  type: number
  /** 是否支持手动新增；0->不支持；1->支持 */
  handAddStatus: number
  /** 可选值列表，以逗号隔开 */
  inputList: string
  /** 属性分类ID */
  productAttributeCategoryId: string
  /** 检索类型；0->不需要进行检索；1->关键字检索；2->范围检索 */
  searchType: number
  /** 属性选择类型：0->唯一；1->单选；2->多选 */
  selectType: number
  /** 相同属性产品是否关联；0->不关联；1->关联 */
  relatedStatus: number
  /** 排序字段：最高的可以单独上传图片 */
  sort: number
}

/** 商品属性值 - 对应后端 PmsProductAttributeValue Schema */
export interface PmsProductAttributeValue {
  /** ID */
  id: string
  /** 属性ID */
  productAttributeId: string
  /** 商品ID */
  productId: string
  /** 手动添加规格或参数的值，参数单值，规格有多个时以逗号隔开 */
  value: string
}

/** 商品SKU库存 - 对应后端 PmsSkuStock Schema */
export interface PmsSkuStock {
  /** SKU ID */
  id: string
  /** sku编码 */
  skuCode: string
  /** 价格 */
  price: number
  /** 库存 */
  stock: number
  /** 单品促销价格 */
  promotionPrice?: number
  /** 商品销售属性，json格式 */
  spData: string
  /** 锁定库存 */
  lockStock: number
  /** 预警库存 */
  lowStock: number
  /** 展示图片 */
  pic: string
  /** 商品ID */
  productId: string
  /** 销量 */
  sale: number
}

/** 商品满减价格 - 对应后端 PmsProductFullReduction Schema */
export interface PmsProductFullReduction {
  /** ID */
  id: string
  /** 商品ID */
  productId: string
  /** 满金额 */
  fullPrice: number
  /** 减金额 */
  reducePrice: number
}

/** 商品阶梯价格 - 对应后端 PmsProductLadder Schema */
export interface PmsProductLadder {
  /** ID */
  id: string
  /** 商品ID */
  productId: string
  /** 满足的商品数量 */
  count: number
  /** 折扣 */
  discount: number
  /** 折后价格 */
  price: number
}

/** 商品详情响应结果 - 对应后端 PortalProductDetailResponse Schema */
export interface PmsPortalProductDetail {
  /** 后端 PortalProductDetailResponse 为扁平商品结构。 */
  id: string
  name: string
  subTitle?: string | null
  brandId?: string | null
  categoryId?: string | null
  productSn?: string | null
  price: number
  originalPrice?: number | null
  promotionPrice?: number | null
  promotionPerLimit?: number
  promotionType?: number
  stock: number
  saleCount?: number
  pics?: string | null
  albumPics?: string | null
  defaultPic?: string | null
  description?: string | null
  keywords?: string | null
  unit?: string | null
  weight?: number | null
  serviceIds?: string | null
  /** SKU 列表 */
  skus: PmsSkuStock[]
  /** 属性值列表 */
  attributeValues: Record<string, unknown>[]
}

/** 规格选项（前端专用） */
export interface SpecOption {
  /** 规格ID */
  pid: number
  /** 规格名称 */
  pname: string
  /** 规格值 */
  name: string
  /** 是否选中 */
  selected?: boolean
}

/** 服务项（前端专用） */
export interface ServiceItem {
  /** 服务ID */
  id: number
  /** 服务名称 */
  name: string
}

/** 分享项（前端专用） */
export interface ShareItem {
  /** 分享类型 */
  type: number
  /** 图标 */
  icon: string
  /** 文字 */
  text: string
}
