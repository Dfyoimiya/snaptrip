/**
 * Global API type definitions — mirrors backend Pydantic schemas (snake_case → camelCase)
 */

// ── Common ────────────────────────────────────────────────────────────────

declare namespace API {
  interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
  }

  interface ApiResponse<T = unknown> {
    code: number;
    message: string;
    data: T;
  }

  // ── Auth ──────────────────────────────────────────────────────────────

  interface LoginRequest {
    email: string;
    password: string;
  }

  interface LoginResponse {
    accessToken: string;
    refreshToken: string;
  }

  interface CurrentUser {
    id: string;
    email: string;
    nickname?: string;
    avatarUrl?: string;
    gender?: number;
  }

  interface AdminUser {
    id: string;
    email: string;
    nickname?: string;
    isActive: boolean;
    createdAt: string;
    roles: Role[];
  }

  // ── Product ───────────────────────────────────────────────────────────

  interface Product {
    id: string;
    name: string;
    subTitle?: string;
    brandId?: string;
    categoryId?: string;
    brandName?: string;
    categoryName?: string;
    productSn?: string;
    price: number;
    originalPrice?: number;
    promotionPrice?: number;
    promotionStartTime?: string;
    promotionEndTime?: string;
    promotionPerLimit: number;
    promotionType: number;
    stock: number;
    saleCount: number;
    pics?: string;
    albumPics?: string;
    defaultPic?: string;
    description?: string;
    keywords?: string;
    unit?: string;
    weight?: number;
    publishStatus: number;
    newStatus: number;
    recommendStatus: number;
    previewStatus: number;
    verifyStatus: number;
    rejectReason?: string;
    serviceIds?: string;
    freightTemplateId?: string;
    createdAt?: string;
    updatedAt?: string;
    skus: Sku[];
    attributeValues: Record<string, string>[];
  }

  interface ProductCreate {
    name: string;
    subTitle?: string;
    brandId?: string;
    categoryId?: string;
    productSn?: string;
    price: number;
    originalPrice?: number;
    promotionPrice?: number;
    promotionStartTime?: string;
    promotionEndTime?: string;
    promotionPerLimit?: number;
    promotionType?: number;
    publishStatus?: number;
    newStatus?: number;
    recommendStatus?: number;
    description?: string;
    keywords?: string;
    unit?: string;
    weight?: number;
    serviceIds?: string;
    freightTemplateId?: string;
    pics?: string;
    albumPics?: string;
    defaultPic?: string;
    skus: SkuCreate[];
    attributeValues: Record<string, string>;
  }

  interface ProductUpdate extends Partial<ProductCreate> {}

  interface Sku {
    id: string;
    productId: string;
    skuCode: string;
    spec: string;
    price: number;
    promotionPrice?: number;
    stock: number;
    lockStock: number;
    lowStock: number;
    saleCount: number;
    pic?: string;
  }

  interface SkuCreate {
    skuCode: string;
    spec: string;
    price: number;
    promotionPrice?: number;
    stock?: number;
    lowStock?: number;
    pic?: string;
  }

  // ── Brand ─────────────────────────────────────────────────────────────

  interface Brand {
    id: string;
    name: string;
    firstLetter?: string;
    sort: number;
    factoryStatus: number;
    showStatus: number;
    logo?: string;
    bigPic?: string;
    brandStory?: string;
    latitude?: number;
    longitude?: number;
    address?: string;
    phone?: string;
    createdAt?: string;
    updatedAt?: string;
  }

  interface BrandCreate {
    name: string;
    firstLetter?: string;
    sort?: number;
    factoryStatus?: number;
    showStatus?: number;
    logo?: string;
    bigPic?: string;
    brandStory?: string;
    latitude?: number;
    longitude?: number;
    address?: string;
    phone?: string;
  }

  interface BrandUpdate extends Partial<BrandCreate> {}

  // ── Category ──────────────────────────────────────────────────────────

  interface Category {
    id: string;
    name: string;
    parentId?: string;
    type?: string;
    level: number;
    sort: number;
    navStatus: number;
    showStatus: number;
    icon?: string;
    keywords?: string;
    description?: string;
    createdAt?: string;
    updatedAt?: string;
  }

  interface CategoryTree extends Category {
    children: CategoryTree[];
  }

  interface CategoryCreate {
    name: string;
    type?: string;
    parentId?: string;
    level?: number;
    sort?: number;
    navStatus?: number;
    showStatus?: number;
    icon?: string;
    keywords?: string;
    description?: string;
  }

  interface CategoryUpdate extends Partial<CategoryCreate> {}

  // ── Product Attribute ─────────────────────────────────────────────────

  interface ProductAttribute {
    id: string;
    categoryId: string;
    name: string;
    attrType: number;
    inputType: number;
    inputList?: string;
    sort: number;
    filterType: number;
    searchType: number;
    relatedStatus: number;
    handAddStatus: number;
  }

  interface ProductAttributeCreate {
    categoryId: string;
    name: string;
    attrType?: number;
    inputType?: number;
    inputList?: string;
    sort?: number;
    filterType?: number;
    searchType?: number;
    relatedStatus?: number;
    handAddStatus?: number;
  }

  // ── Order ─────────────────────────────────────────────────────────────

  interface Order {
    id: string;
    orderSn: string;
    userId: string;
    memberUsername: string;
    totalAmount: number;
    payAmount: number;
    freightAmount: number;
    discountAmount: number;
    payType: number;
    paymentTime?: string;
    deliveryCompany?: string;
    deliverySn?: string;
    deliveryTime?: string;
    receiverName: string;
    receiverPhone: string;
    receiverProvince?: string;
    receiverCity?: string;
    receiverRegion?: string;
    receiverDetailAddress: string;
    receiverPostCode?: string;
    status: number;
    note?: string;
    createdAt?: string;
    updatedAt?: string;
    items: OrderItem[];
    logs: OrderLog[];
  }

  interface OrderItem {
    id: string;
    productId: string;
    productName: string;
    productPic?: string;
    skuId: string;
    skuCode: string;
    spec: string;
    price: number;
    quantity: number;
  }

  interface OrderLog {
    id: string;
    operateMan: string;
    orderStatusBefore?: number;
    orderStatusAfter: number;
    note?: string;
    createdAt?: string;
  }

  interface OrderDelivery {
    deliveryCompany: string;
    deliverySn: string;
  }

  interface OrderPriceModify {
    freightAmount?: number;
    discountAmount?: number;
  }

  // ── Return Apply ──────────────────────────────────────────────────────

  interface ReturnApply {
    id: string;
    orderId: string;
    orderSn: string;
    memberUsername: string;
    productId: string;
    productName: string;
    productPic?: string;
    productAttr?: string;
    productPrice: number;
    productRealPrice: number;
    productCount: number;
    reason: string;
    description?: string;
    proofPics?: string;
    status: number;
    handleMan?: string;
    handleNote?: string;
    handleTime?: string;
    returnAmount?: number;
    returnName: string;
    returnPhone: string;
    createdAt?: string;
  }

  interface ReturnApplyStatusUpdate {
    status: number;
    handleNote?: string;
    returnAmount?: number;
  }

  // ── Return Reason ─────────────────────────────────────────────────────

  interface ReturnReason {
    id: string;
    name: string;
    sort: number;
    status: number;
    createdAt?: string;
  }

  // ── Member ────────────────────────────────────────────────────────────

  interface Member {
    id: string;
    email: string;
    isActive: boolean;
    createdAt?: string;
  }

  // ── Coupon ────────────────────────────────────────────────────────────

  interface Coupon {
    id: string;
    name: string;
    type: number;
    useType: number;
    amount: number;
    minAmount: number;
    categoryId?: string;
    brandId?: string;
    count: number;
    publishCount: number;
    receiveCount: number;
    useCount: number;
    perLimit: number;
    startTime?: string;
    endTime?: string;
    status: number;
    note?: string;
    createdAt?: string;
  }

  interface CouponCreate {
    name: string;
    type?: number;
    useType?: number;
    amount: number;
    minAmount?: number;
    categoryId?: string;
    brandId?: string;
    count: number;
    perLimit?: number;
    startTime?: string;
    endTime?: string;
    status?: number;
    memberLevel?: number;
    note?: string;
  }

  interface CouponUpdate extends Partial<CouponCreate> {}

  interface CouponHistory {
    id: string;
    couponId: string;
    userId: string;
    couponName: string;
    couponAmount: number;
    couponMinAmount: number;
    useStatus: number;
    useTime?: string;
    orderId?: string;
    orderSn?: string;
    receiveTime: string;
    expireTime: string;
  }

  // ── Flash Promotion ───────────────────────────────────────────────────

  interface FlashPromotion {
    id: string;
    title: string;
    startDate: string;
    endDate: string;
    status: number;
    note?: string;
    createdAt?: string;
  }

  interface FlashPromotionCreate {
    title: string;
    startDate: string;
    endDate: string;
    note?: string;
  }

  interface FlashSession {
    id: string;
    promotionId: string;
    name: string;
    startTime: string;
    endTime: string;
    status: number;
  }

  interface FlashSessionCreate {
    promotionId: string;
    name: string;
    startTime: string;
    endTime: string;
  }

  interface FlashProduct {
    id: string;
    sessionId: string;
    productId: string;
    skuId: string;
    flashPrice: number;
    flashStock: number;
    flashLimit: number;
    sort: number;
  }

  interface FlashProductCreate {
    sessionId: string;
    productId: string;
    skuId: string;
    flashPrice: number;
    flashStock: number;
    flashLimit?: number;
    sort?: number;
  }

  // ── CMS ───────────────────────────────────────────────────────────────

  interface Banner {
    id: string;
    title: string;
    pic: string;
    url?: string;
    position: string;
    sort: number;
    status: number;
    startTime?: string;
    endTime?: string;
    createdAt?: string;
  }

  interface BannerCreate {
    title: string;
    pic: string;
    url?: string;
    position?: string;
    sort?: number;
    status?: number;
    startTime?: string;
    endTime?: string;
  }

  interface BannerUpdate extends Partial<BannerCreate> {}

  interface Subject {
    id: string;
    title: string;
    summary?: string;
    pic?: string;
    content?: string;
    categoryName?: string;
    status: number;
    recommendStatus: number;
    createdAt?: string;
  }

  interface SubjectCreate {
    title: string;
    summary?: string;
    pic?: string;
    content?: string;
    categoryName?: string;
    status?: number;
    recommendStatus?: number;
  }

  interface SubjectUpdate extends Partial<SubjectCreate> {}

  interface Help {
    id: string;
    title: string;
    content?: string;
    categoryName?: string;
    status: number;
    sort: number;
    createdAt?: string;
  }

  interface HelpCreate {
    title: string;
    content?: string;
    categoryName?: string;
    status?: number;
    sort?: number;
  }

  // ── Notice ────────────────────────────────────────────────────────────

  interface Notice {
    id: string;
    title: string;
    content?: string;
    targetType: string;
    status: number;
    publishTime?: string;
    createdAt?: string;
    updatedAt?: string;
  }

  interface NoticeCreate {
    title: string;
    content?: string;
    targetType?: string;
  }

  interface NoticeUpdate extends Partial<NoticeCreate> {}

  // ── CS Ticket ─────────────────────────────────────────────────────────

  interface CsTicket {
    id: string;
    orderId?: string;
    memberId: string;
    type: string;
    status: string;
    priority: string;
    title: string;
    description?: string;
    resolution?: string;
    satisfactionScore?: number;
    escalatedTo?: string;
    assignedAgentId?: string;
    slaDeadline?: string;
    firstResponseAt?: string;
    tags?: string[];
    resolvedAt?: string;
    createdAt?: string;
    updatedAt?: string;
  }

  interface CsMessage {
    id: string;
    ticketId: string;
    senderType: string;
    senderId?: string;
    content: string;
    content_type: string;
    createdAt: string;
  }

  // ── Role / Menu / Resource ────────────────────────────────────────────

  interface Role {
    id: string;
    name: string;
    description?: string;
    status: number;
    sort: number;
    createdAt?: string;
  }

  interface RoleCreate {
    name: string;
    description?: string;
    status?: number;
    sort?: number;
  }

  interface MenuNode {
    id: string;
    parentId?: string;
    title: string;
    name?: string;
    icon?: string;
    sort: number;
    hidden: number;
    level: number;
    children: MenuNode[];
  }

  interface Resource {
    id: string;
    categoryId?: string;
    name: string;
    url?: string;
    description?: string;
    createdAt?: string;
  }

  interface ResourceCategory {
    id: string;
    name: string;
    sort: number;
    createdAt?: string;
  }

  // ── Dashboard ─────────────────────────────────────────────────────────

  interface DashboardData {
    todayOrders: number;
    todayRevenue: number;
    todayRevenueDisplay: string;
    pendingReturns: number;
    newMembers: number;
    orderStatusCounts: Record<string, number>;
    topProducts: { productId: string; productName: string; saleCount: number; amount: number }[];
    weekDays: string[];
    weekSales: number[];
    latestOrders: Order[];
  }

  interface StatsOverview {
    todayOrderCount: number;
    todaySalesAmount: number;
    todayNewMemberCount: number;
    totalProductCount: number;
    onShelfProductCount: number;
  }

  interface SalesStatItem {
    date: string;
    amount: number;
    orderCount: number;
  }

  interface ProductRankItem {
    productId: string;
    productName: string;
    saleCount: number;
    amount: number;
  }
}

export {};
