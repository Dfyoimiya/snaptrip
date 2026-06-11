<script setup lang="ts">
/**
 * ============================================
 * 商品搜索列表页 (SearchView)
 * 合并搜索和列表功能
 * 顶部：复杂筛选区（分类、品牌、价格区间、排序）
 * 中部：标准 4 列网格商品卡片
 * 底部：分页器
 * 支持 Keyword + CategoryId + BrandId 组合查询
 * ============================================
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { PmsProduct } from '@/types/product'

const route = useRoute()
const router = useRouter()

// ===== 筛选状态 =====
const keyword = ref((route.query.keyword as string) || '')
const categoryId = ref<number | undefined>(route.query.categoryId ? Number(route.query.categoryId) : undefined)
const brandId = ref<number | undefined>(route.query.brandId ? Number(route.query.brandId) : undefined)
const sortType = ref(0)
const minPrice = ref<number | undefined>(undefined)
const maxPrice = ref<number | undefined>(undefined)
const currentPage = ref(1)
const pageSize = 20
const loading = ref(false)

// ===== 数据 =====
const total = ref(0)
const productList = ref<PmsProduct[]>([])

/** 排序选项 */
const sortOptions = [
  { label: '综合排序', value: 0 },
  { label: '销量', value: 2, icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
  { label: '价格从低到高', value: 3 },
  { label: '价格从高到低', value: 4 },
]

/** 分类筛选选项 */
const categoryOptions = [
  { id: 1, name: '手机数码' },
  { id: 2, name: '电脑办公' },
  { id: 3, name: '家用电器' },
  { id: 4, name: '家居家装' },
  { id: 5, name: '服装服饰' },
  { id: 6, name: '美妆个护' },
  { id: 7, name: '运动户外' },
  { id: 8, name: '食品生鲜' },
]

/** 品牌筛选选项 */
const brandOptions = [
  { id: 1, name: 'Apple' },
  { id: 2, name: '华为' },
  { id: 3, name: '小米' },
  { id: 4, name: 'Nike' },
  { id: 5, name: 'Adidas' },
  { id: 6, name: 'Sony' },
  { id: 7, name: 'Dyson' },
  { id: 8, name: '三星' },
  { id: 9, name: '联想' },
  { id: 10, name: '海尔' },
]

/** 价格区间预设 */
const priceRanges = [
  { label: '0-500', min: 0, max: 500 },
  { label: '500-1000', min: 500, max: 1000 },
  { label: '1000-3000', min: 1000, max: 3000 },
  { label: '3000-5000', min: 3000, max: 5000 },
  { label: '5000+', min: 5000, max: undefined },
]

/** 选中的价格区间索引 */
const selectedPriceRange = ref(-1)

// ===== Mock 商品数据池 =====
const mockProducts: PmsProduct[] = [
  { id: 1, name: 'Apple iPhone 15 Pro Max 256GB 钛金属 5G智能手机', pic: 'https://images.unsplash.com/photo-1696446701796-da61225697cc?w=300&h=300&fit=crop', price: 9999, originalPrice: 10999, sale: 5200, stock: 200, brandId: 1, brandName: 'Apple', productCategoryId: 1, productCategoryName: '手机数码', subTitle: 'A17 Pro芯片', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 1, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 2, name: '华为 Mate 60 Pro 12GB+512GB 鸿蒙系统 卫星通信', pic: 'https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=300&h=300&fit=crop', price: 6999, originalPrice: 7999, sale: 8900, stock: 150, brandId: 2, brandName: '华为', productCategoryId: 1, productCategoryName: '手机数码', subTitle: '麒麟9000S', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 2, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 3, name: '小米14 Pro 16GB+512GB 徕卡影像 骁龙8 Gen3', pic: 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300&h=300&fit=crop', price: 5499, originalPrice: 5999, sale: 12000, stock: 300, brandId: 3, brandName: '小米', productCategoryId: 1, productCategoryName: '手机数码', subTitle: '徕卡Summilux', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 3, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 4, name: 'Apple MacBook Air M3芯片 13.6英寸 16GB+512GB', pic: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', price: 10499, originalPrice: 11999, sale: 3200, stock: 80, brandId: 1, brandName: 'Apple', productCategoryId: 2, productCategoryName: '电脑办公', subTitle: 'M3芯片', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 4, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 5, name: '联想 ThinkPad X1 Carbon 2024 14英寸轻薄商务本', pic: 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=300&h=300&fit=crop', price: 12999, originalPrice: 14999, sale: 1800, stock: 60, brandId: 9, brandName: '联想', productCategoryId: 2, productCategoryName: '电脑办公', subTitle: '碳纤维机身', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 5, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 6, name: 'Sony WH-1000XM5 头戴式无线降噪耳机 铂金银', pic: 'https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?w=300&h=300&fit=crop', price: 2499, originalPrice: 2999, sale: 6500, stock: 120, brandId: 6, brandName: 'Sony', productCategoryId: 1, productCategoryName: '手机数码', subTitle: 'AI降噪', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 6, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 7, name: 'Dyson Supersonic HD15 吹风机 镍灰色 负离子护发', pic: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=300&h=300&fit=crop', price: 2590, originalPrice: 3290, sale: 8900, stock: 100, brandId: 7, brandName: 'Dyson', productCategoryId: 3, productCategoryName: '家用电器', subTitle: '智能温控', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 7, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 8, name: 'Nike Air Force 1 \'07 空军一号 白色 42码', pic: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300&h=300&fit=crop', price: 749, originalPrice: 899, sale: 25000, stock: 500, brandId: 4, brandName: 'Nike', productCategoryId: 5, productCategoryName: '服装服饰', subTitle: '经典百搭', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 8, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 9, name: '三星 65英寸 QLED 4K超高清智能电视 QA65Q70C', pic: 'https://images.unsplash.com/photo-1593784991095-a205069470b6?w=300&h=300&fit=crop', price: 6999, originalPrice: 8999, sale: 2100, stock: 45, brandId: 8, brandName: '三星', productCategoryId: 3, productCategoryName: '家用电器', subTitle: '量子点技术', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 9, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 10, name: '海尔 545升 十字对开门冰箱 一级能效变频', pic: 'https://images.unsplash.com/photo-1584568694244-067fb5f30001?w=300&h=300&fit=crop', price: 4299, originalPrice: 5899, sale: 3500, stock: 70, brandId: 10, brandName: '海尔', productCategoryId: 3, productCategoryName: '家用电器', subTitle: '双变频养鲜', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 10, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 11, name: 'Adidas Ultraboost 22 跑步鞋 黑色 43码', pic: 'https://images.unsplash.com/photo-1584735175315-9d5df23860e6?w=300&h=300&fit=crop', price: 899, originalPrice: 1299, sale: 8000, stock: 200, brandId: 5, brandName: 'Adidas', productCategoryId: 5, productCategoryName: '服装服饰', subTitle: 'Boost中底', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 11, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 12, name: '华为 MatePad Pro 13.2英寸 144Hz OLED平板', pic: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=300&h=300&fit=crop', price: 4999, originalPrice: 5699, sale: 1500, stock: 90, brandId: 2, brandName: '华为', productCategoryId: 2, productCategoryName: '电脑办公', subTitle: '星闪手写笔', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 12, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 13, name: 'Apple Watch Series 9 GPS版 45mm 星光色', pic: 'https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=300&h=300&fit=crop', price: 2999, originalPrice: 3499, sale: 4200, stock: 150, brandId: 1, brandName: 'Apple', productCategoryId: 1, productCategoryName: '手机数码', subTitle: 'S9 SiP芯片', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 13, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 14, name: '小米电视 S Pro 75英寸 Mini LED 4K 144Hz', pic: 'https://images.unsplash.com/photo-1593784991095-a205069470b6?w=300&h=300&fit=crop', price: 5999, originalPrice: 7999, sale: 2800, stock: 55, brandId: 3, brandName: '小米', productCategoryId: 3, productCategoryName: '家用电器', subTitle: '千级分区', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 14, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 15, name: 'Sony A7M4 全画幅微单相机 单机身 ILCE-7M4', pic: 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=300&h=300&fit=crop', price: 16999, originalPrice: 18999, sale: 900, stock: 30, brandId: 6, brandName: 'Sony', productCategoryId: 1, productCategoryName: '手机数码', subTitle: '3300万像素', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 15, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 16, name: 'Nintendo Switch OLED 游戏主机 日版 红蓝', pic: 'https://images.unsplash.com/photo-1578303512597-81e6cc155b3e?w=300&h=300&fit=crop', price: 1899, originalPrice: 2599, sale: 15000, stock: 200, brandId: 1, brandName: 'Nintendo', productCategoryId: 7, productCategoryName: '运动户外', subTitle: 'OLED屏幕', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 16, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 17, name: 'SK-II 神仙水护肤精华露 230ml 补水保湿', pic: 'https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=300&h=300&fit=crop', price: 1540, originalPrice: 2150, sale: 12000, stock: 300, brandId: 4, brandName: 'SK-II', productCategoryId: 6, productCategoryName: '美妆个护', subTitle: 'PITERA精华', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 17, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 18, name: 'Dyson V12 Detect Slim 吸尘器 激光探测', pic: 'https://images.unsplash.com/photo-1558317374-067fb5f30001?w=300&h=300&fit=crop', price: 4490, originalPrice: 5290, sale: 2500, stock: 65, brandId: 7, brandName: 'Dyson', productCategoryId: 3, productCategoryName: '家用电器', subTitle: '激光除尘', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 18, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 19, name: 'AirPods Pro 2 配MagSafe充电盒 USB-C', pic: 'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=300&h=300&fit=crop', price: 1899, originalPrice: 2199, sale: 18000, stock: 400, brandId: 1, brandName: 'Apple', productCategoryId: 1, productCategoryName: '手机数码', subTitle: 'H2芯片', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 19, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 20, name: '华为 FreeBuds Pro 3 无线耳机 星闪连接', pic: 'https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=300&h=300&fit=crop', price: 1299, originalPrice: 1599, sale: 5600, stock: 180, brandId: 2, brandName: '华为', productCategoryId: 1, productCategoryName: '手机数码', subTitle: '无损音质', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 1, recommandStatus: 1, verifyStatus: 1, sort: 20, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 21, name: '小米空气净化器 4 Pro H 除甲醛除菌', pic: 'https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=300&h=300&fit=crop', price: 1699, originalPrice: 2299, sale: 8000, stock: 120, brandId: 3, brandName: '小米', productCategoryId: 3, productCategoryName: '家用电器', subTitle: '固态甲醛传感', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 21, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 22, name: '联想拯救者 Y9000P 2024 RTX4060 电竞本', pic: 'https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=300&h=300&fit=crop', price: 9999, originalPrice: 11999, sale: 2100, stock: 50, brandId: 9, brandName: '联想', productCategoryId: 2, productCategoryName: '电脑办公', subTitle: 'i9-14900HX', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 22, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 23, name: 'Adidas Originals Forum Low 复古板鞋', pic: 'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=300&h=300&fit=crop', price: 799, originalPrice: 999, sale: 6000, stock: 250, brandId: 5, brandName: 'Adidas', productCategoryId: 5, productCategoryName: '服装服饰', subTitle: '复古篮球风', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 23, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
  { id: 24, name: '三星 Galaxy Watch6 Classic 47mm 蓝牙版', pic: 'https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=300&h=300&fit=crop', price: 2299, originalPrice: 2899, sale: 1800, stock: 80, brandId: 8, brandName: '三星', productCategoryId: 1, productCategoryName: '手机数码', subTitle: '旋转表圈', productSn: '', albumPics: '', description: '', detailTitle: '', detailMobileHtml: '', publishStatus: 1, newStatus: 0, recommandStatus: 1, verifyStatus: 1, sort: 24, promotionPrice: 0, promotionType: 0, promotionStartTime: '', promotionEndTime: '', serviceIds: '', createTime: '', updateTime: '' },
]

// ===== 筛选逻辑（前端过滤） =====
const filteredProducts = computed(() => {
  let result = [...mockProducts]

  // 关键词过滤
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    result = result.filter(p =>
      p.name.toLowerCase().includes(kw) ||
      p.brandName.toLowerCase().includes(kw) ||
      p.subTitle.toLowerCase().includes(kw),
    )
  }

  // 分类过滤
  if (categoryId.value) {
    result = result.filter(p => p.productCategoryId === categoryId.value)
  }

  // 品牌过滤
  if (brandId.value) {
    result = result.filter(p => p.brandId === brandId.value)
  }

  // 价格区间过滤
  if (minPrice.value !== undefined) {
    result = result.filter(p => p.price >= minPrice.value!)
  }
  if (maxPrice.value !== undefined) {
    result = result.filter(p => p.price <= maxPrice.value!)
  }

  // 排序
  if (sortType.value === 2) {
    // 销量降序
    result.sort((a, b) => b.sale - a.sale)
  } else if (sortType.value === 3) {
    // 价格升序
    result.sort((a, b) => a.price - b.price)
  } else if (sortType.value === 4) {
    // 价格降序
    result.sort((a, b) => b.price - a.price)
  }

  return result
})

/** 总页数 */
const totalPages = computed(() => Math.ceil(filteredProducts.value.length / pageSize))

/** 分页后的商品 */
const paginatedProducts = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredProducts.value.slice(start, start + pageSize)
})

/** 已选筛选标签 */
const activeFilters = computed(() => {
  const filters: { key: string; label: string }[] = []
  if (categoryId.value) {
    const cat = categoryOptions.find(c => c.id === categoryId.value)
    if (cat) filters.push({ key: 'category', label: `分类: ${cat.name}` })
  }
  if (brandId.value) {
    const brand = brandOptions.find(b => b.id === brandId.value)
    if (brand) filters.push({ key: 'brand', label: `品牌: ${brand.name}` })
  }
  if (minPrice.value !== undefined || maxPrice.value !== undefined) {
    const min = minPrice.value ?? 0
    const max = maxPrice.value ?? '∞'
    filters.push({ key: 'price', label: `价格: ¥${min}-${max}` })
  }
  return filters
})

/** 是否有筛选条件 */
const hasActiveFilters = computed(() => activeFilters.value.length > 0)

// ===== 操作 =====
const selectCategory = (id: number) => {
  categoryId.value = categoryId.value === id ? undefined : id
  currentPage.value = 1
}

const selectBrand = (id: number) => {
  brandId.value = brandId.value === id ? undefined : id
  currentPage.value = 1
}

const selectPriceRange = (index: number) => {
  if (selectedPriceRange.value === index) {
    selectedPriceRange.value = -1
    minPrice.value = undefined
    maxPrice.value = undefined
  } else {
    selectedPriceRange.value = index
    const range = priceRanges[index]
    minPrice.value = range.min
    maxPrice.value = range.max
  }
  currentPage.value = 1
}

const handleSortChange = (sort: number) => {
  sortType.value = sort
  currentPage.value = 1
}

const removeFilter = (key: string) => {
  if (key === 'category') categoryId.value = undefined
  if (key === 'brand') brandId.value = undefined
  if (key === 'price') {
    minPrice.value = undefined
    maxPrice.value = undefined
    selectedPriceRange.value = -1
  }
  currentPage.value = 1
}

const clearAllFilters = () => {
  categoryId.value = undefined
  brandId.value = undefined
  minPrice.value = undefined
  maxPrice.value = undefined
  selectedPriceRange.value = -1
  sortType.value = 0
  currentPage.value = 1
}

const goPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
}

const goProductDetail = (id: number) => {
  router.push(`/product/${id}`)
}

// 同步 URL 参数变化
watch(
  () => [route.query.keyword, route.query.categoryId, route.query.brandId],
  ([kw, cat, brand]) => {
    keyword.value = (kw as string) || ''
    categoryId.value = cat ? Number(cat) : undefined
    brandId.value = brand ? Number(brand) : undefined
    currentPage.value = 1
    total.value = filteredProducts.value.length
  },
  { immediate: true },
)

onMounted(() => {
  total.value = filteredProducts.value.length
})
</script>

<template>
  <div class="search-page space-y-4">
    <!-- ====== 搜索结果头部 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 px-6 py-4">
      <div class="flex items-center justify-between">
        <h1 class="text-lg font-bold text-gray-900">
          <span v-if="keyword">"{{ keyword }}" 的搜索结果</span>
          <span v-else>全部商品</span>
          <span class="text-sm font-normal text-gray-400 ml-2">共 {{ filteredProducts.length }} 件商品</span>
        </h1>
        <!-- 排序按钮 -->
        <div class="flex items-center gap-1">
          <button
            v-for="opt in sortOptions"
            :key="opt.value"
            :class="[
              'px-3 py-1.5 text-sm rounded-md transition-colors',
              sortType === opt.value
                ? 'bg-red-600 text-white font-medium'
                : 'text-gray-600 hover:bg-gray-100',
            ]"
            @click="handleSortChange(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- ====== 筛选区 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 divide-y divide-gray-100">
      <!-- 分类筛选 -->
      <div class="flex items-start px-6 py-3.5 gap-3">
        <span class="text-sm text-gray-500 w-14 flex-shrink-0 pt-1">分类</span>
        <div class="flex flex-wrap gap-2 flex-1">
          <button
            v-for="cat in categoryOptions"
            :key="cat.id"
            :class="[
              'px-3 py-1 text-sm rounded-md transition-colors',
              categoryId === cat.id
                ? 'bg-red-600 text-white'
                : 'text-gray-600 bg-gray-50 hover:bg-red-50 hover:text-red-600',
            ]"
            @click="selectCategory(cat.id)"
          >
            {{ cat.name }}
          </button>
        </div>
      </div>

      <!-- 品牌筛选 -->
      <div class="flex items-start px-6 py-3.5 gap-3">
        <span class="text-sm text-gray-500 w-14 flex-shrink-0 pt-1">品牌</span>
        <div class="flex flex-wrap gap-2 flex-1">
          <button
            v-for="brand in brandOptions"
            :key="brand.id"
            :class="[
              'px-3 py-1 text-sm rounded-md transition-colors',
              brandId === brand.id
                ? 'bg-red-600 text-white'
                : 'text-gray-600 bg-gray-50 hover:bg-red-50 hover:text-red-600',
            ]"
            @click="selectBrand(brand.id)"
          >
            {{ brand.name }}
          </button>
        </div>
      </div>

      <!-- 价格区间 -->
      <div class="flex items-start px-6 py-3.5 gap-3">
        <span class="text-sm text-gray-500 w-14 flex-shrink-0 pt-1">价格</span>
        <div class="flex items-center gap-2 flex-1">
          <button
            v-for="(range, index) in priceRanges"
            :key="index"
            :class="[
              'px-3 py-1 text-sm rounded-md transition-colors',
              selectedPriceRange === index
                ? 'bg-red-600 text-white'
                : 'text-gray-600 bg-gray-50 hover:bg-red-50 hover:text-red-600',
            ]"
            @click="selectPriceRange(index)"
          >
            ¥{{ range.min }}<template v-if="range.max !== undefined">-{{ range.max }}</template><template v-else>以上</template>
          </button>
          <div class="flex items-center gap-1 ml-2">
            <input
              v-model.number="minPrice"
              type="number"
              placeholder="¥最低"
              class="w-20 h-7 px-2 border border-gray-200 rounded text-sm text-center focus:outline-none focus:border-red-500"
              @blur="currentPage = 1"
            />
            <span class="text-gray-300">-</span>
            <input
              v-model.number="maxPrice"
              type="number"
              placeholder="¥最高"
              class="w-20 h-7 px-2 border border-gray-200 rounded text-sm text-center focus:outline-none focus:border-red-500"
              @blur="currentPage = 1"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- ====== 已选筛选标签 ====== -->
    <div v-if="hasActiveFilters" class="flex items-center gap-2">
      <span class="text-sm text-gray-500">已选：</span>
      <span
        v-for="filter in activeFilters"
        :key="filter.key"
        class="inline-flex items-center gap-1 px-2.5 py-1 bg-red-50 text-red-600 text-xs rounded-full"
      >
        {{ filter.label }}
        <button class="hover:text-red-800" @click="removeFilter(filter.key)">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </span>
      <button class="text-xs text-gray-500 hover:text-red-600 ml-2" @click="clearAllFilters">清除全部</button>
    </div>

    <!-- ====== 商品网格 ====== -->
    <div v-if="paginatedProducts.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <button
        v-for="product in paginatedProducts"
        :key="product.id"
        class="group text-left bg-white rounded-xl border border-gray-100 hover:border-red-200 hover:-translate-y-0.5 hover:shadow-lg transition-all duration-300 overflow-hidden"
        @click="goProductDetail(product.id)"
      >
        <!-- 商品图片 -->
        <div class="aspect-square bg-gray-50 overflow-hidden relative">
          <img :src="product.pic" :alt="product.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          <!-- 促销标签 -->
          <span
            v-if="product.originalPrice > product.price"
            class="absolute top-2 left-2 bg-red-600 text-white text-[10px] px-1.5 py-0.5 rounded font-medium"
          >
            省{{ Math.round((1 - product.price / product.originalPrice) * 100) }}%
          </span>
        </div>
        <!-- 商品信息 -->
        <div class="p-3.5">
          <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">{{ product.name }}</p>
          <div class="flex items-baseline gap-2">
            <span class="text-red-600 font-bold text-base"><span class="text-xs">&yen;</span>{{ product.price }}</span>
            <span class="text-xs text-gray-400 line-through">&yen;{{ product.originalPrice }}</span>
          </div>
          <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-gray-400">已售 {{ product.sale >= 10000 ? (product.sale / 10000).toFixed(1) + '万' : product.sale }}</span>
            <span class="text-xs text-gray-400">{{ product.brandName }}</span>
          </div>
        </div>
      </button>
    </div>

    <!-- ====== 空状态 ====== -->
    <div v-else class="bg-white rounded-xl border border-gray-100 py-20 flex flex-col items-center text-gray-400">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
        <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      <p class="text-lg">未找到符合条件的商品</p>
      <button class="mt-4 text-sm text-red-600 hover:text-red-700" @click="clearAllFilters">清除筛选条件</button>
    </div>

    <!-- ====== 分页器 ====== -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-1.5 py-4">
      <button
        class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
        :disabled="currentPage === 1"
        @click="goPage(currentPage - 1)"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <button
        v-for="page in totalPages"
        :key="page"
        :class="[
          'min-w-9 h-9 px-2.5 flex items-center justify-center rounded-md text-sm transition-colors',
          currentPage === page
            ? 'bg-red-600 text-white font-medium'
            : 'border border-gray-200 text-gray-600 hover:bg-gray-50',
        ]"
        @click="goPage(page)"
      >
        {{ page }}
      </button>

      <button
        class="w-9 h-9 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
        :disabled="currentPage === totalPages"
        @click="goPage(currentPage + 1)"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>

      <span class="text-sm text-gray-400 ml-3">
        第 {{ currentPage }} / {{ totalPages }} 页，共 {{ filteredProducts.length }} 件
      </span>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
