<script setup lang="ts">
/**
 * ============================================
 * 商城首页 (HomeView)
 * 参考京东/天猫/淘宝 PC 端经典布局
 * ============================================
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// ===== 轮播图 =====
const currentBanner = ref(0)
let bannerTimer: ReturnType<typeof setInterval> | null = null

const banners = ref([
  { id: 1, img: 'https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=960&h=400&fit=crop', title: '年中大促 全场5折起', subtitle: '万件好物限时抢购' },
  { id: 2, img: 'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=960&h=400&fit=crop', title: '时尚潮流 新品首发', subtitle: '大牌联名限量发售' },
  { id: 3, img: 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=960&h=400&fit=crop', title: '智能家电 品质生活', subtitle: '精选好物 惊喜优惠' },
  { id: 4, img: 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=960&h=400&fit=crop', title: '品质家居 焕新升级', subtitle: '打造理想生活空间' },
])

const startBannerAutoPlay = () => {
  bannerTimer = setInterval(() => {
    currentBanner.value = (currentBanner.value + 1) % banners.value.length
  }, 4000)
}

const stopBannerAutoPlay = () => {
  if (bannerTimer) {
    clearInterval(bannerTimer)
    bannerTimer = null
  }
}

const goToBanner = (index: number) => {
  currentBanner.value = index
  stopBannerAutoPlay()
  startBannerAutoPlay()
}

// ===== 多级商品分类 =====
interface SubCategory {
  name: string
  items: string[]
}

interface Category {
  name: string
  icon: string
  subCategories: SubCategory[]
}

const categories = ref<Category[]>([
  {
    name: '手机数码',
    icon: '📱',
    subCategories: [
      { name: '手机通讯', items: ['5G手机', '游戏手机', '拍照手机', '全面屏手机', '对讲机', '以旧换新'] },
      { name: '手机配件', items: ['手机壳', '贴膜', '移动电源', '数据线', '充电器', '手机存储卡', '创意配件'] },
      { name: '摄影摄像', items: ['数码相机', '微单相机', '单反相机', '拍立得', '运动相机', '摄像机', '镜头'] },
      { name: '数码配件', items: ['存储卡', '读卡器', '三脚架', '相机包', '滤镜', '电池/充电器'] },
    ],
  },
  {
    name: '电脑办公',
    icon: '💻',
    subCategories: [
      { name: '电脑整机', items: ['轻薄本', '游戏本', '台式机', '一体机', '平板电脑', '服务器'] },
      { name: '电脑配件', items: ['显示器', 'CPU', '主板', '显卡', '硬盘', '内存', '机箱', '电源'] },
      { name: '外设产品', items: ['鼠标', '键盘', 'U盘', '移动硬盘', '鼠标垫', '摄像头', '线缆'] },
      { name: '办公设备', items: ['投影机', '打印机', '碎纸机', '考勤机', '保险柜', '白板'] },
    ],
  },
  {
    name: '家用电器',
    icon: '🏠',
    subCategories: [
      { name: '电视', items: ['超薄电视', '全面屏', '4K超清', '智能电视', 'OLED电视', '98英寸'] },
      { name: '空调', items: ['壁挂式', '柜机', '中央空调', '移动空调', '变频空调', '一级能效'] },
      { name: '冰箱', items: ['对开门', '三门', '双门', '冷柜/冰吧', '酒柜', '多门'] },
      { name: '洗衣机', items: ['滚筒', '洗烘一体', '波轮', '迷你', '烘干机', '双缸'] },
      { name: '厨卫大电', items: ['油烟机', '燃气灶', '洗碗机', '电热水器', '燃气热水器', '消毒柜'] },
    ],
  },
  {
    name: '家居家装',
    icon: '🛋️',
    subCategories: [
      { name: '家纺', items: ['床品套件', '被子', '枕头', '蚊帐', '凉席', '毛巾浴巾', '地毯地垫'] },
      { name: '灯具', items: ['吸顶灯', '吊灯', '台灯', '筒灯射灯', '灯带', '户外灯'] },
      { name: '家具', items: ['沙发', '床', '床垫', '餐桌', '衣柜', '茶几', '鞋柜'] },
      { name: '厨具', items: ['炒锅', '压力锅', '蒸锅', '炖锅', '煎锅', '汤锅', '奶锅'] },
      { name: '水具酒具', items: ['保温杯', '茶壶', '咖啡具', '玻璃杯', '陶瓷杯', '酒具'] },
    ],
  },
  {
    name: '服装服饰',
    icon: '👗',
    subCategories: [
      { name: '女装', items: ['连衣裙', 'T恤', '衬衫', '卫衣', '外套', '牛仔裤', '半身裙'] },
      { name: '男装', items: ['T恤', '衬衫', 'POLO衫', '夹克', '西服', '休闲裤', '牛仔裤'] },
      { name: '童装', items: ['套装', '上衣', '裤子', '裙子', '亲子装', '童鞋', '婴儿装'] },
      { name: '内衣', items: ['文胸', '内裤', '睡衣', '保暖内衣', '袜子', '塑身衣'] },
      { name: '配饰', items: ['围巾', '帽子', '手套', '皮带', '太阳镜', '首饰'] },
    ],
  },
  {
    name: '美妆个护',
    icon: '💄',
    subCategories: [
      { name: '面部护肤', items: ['洁面', '爽肤水', '乳液/面霜', '精华', '面膜', '防晒', '眼霜'] },
      { name: '彩妆香氛', items: ['口红', '粉底', '眼影', '香水', '眉笔', '腮红', '卸妆'] },
      { name: '美发护发', items: ['洗发水', '护发素', '染发', '造型', '发膜', '精油'] },
      { name: '身体护理', items: ['沐浴露', '身体乳', '护手霜', '剃须', '脱毛', '足浴'] },
      { name: '口腔护理', items: ['牙膏', '牙刷', '漱口水', '牙线', '电动牙刷', '冲牙器'] },
    ],
  },
  {
    name: '运动户外',
    icon: '⚽',
    subCategories: [
      { name: '运动鞋包', items: ['跑步鞋', '休闲鞋', '篮球鞋', '足球鞋', '板鞋', '运动包'] },
      { name: '运动服饰', items: ['运动T恤', '运动裤', '卫衣', '夹克', '运动套装', '健身服'] },
      { name: '健身训练', items: ['跑步机', '动感单车', '哑铃', '瑜伽垫', '健腹轮', '跳绳'] },
      { name: '户外装备', items: ['帐篷', '背包', '睡袋', '登山鞋', '冲锋衣', '户外照明'] },
      { name: '体育用品', items: ['乒乓球', '羽毛球', '篮球', '足球', '网球', '台球'] },
    ],
  },
  {
    name: '食品生鲜',
    icon: '🍎',
    subCategories: [
      { name: '新鲜水果', items: ['苹果', '橙子', '芒果', '葡萄', '西瓜', '车厘子', '榴莲'] },
      { name: '海鲜水产', items: ['虾类', '鱼类', '蟹类', '贝类', '海参', '鱿鱼', '小龙虾'] },
      { name: '肉禽蛋品', items: ['牛肉', '猪肉', '羊肉', '鸡肉', '鸡蛋', '牛排', '鸡翅'] },
      { name: '粮油调味', items: ['大米', '食用油', '面粉', '酱油', '调味酱', '干货'] },
      { name: '休闲食品', items: ['坚果', '饼干', '巧克力', '糖果', '肉干', '蜜饯', '薯片'] },
    ],
  },
  {
    name: '母婴玩具',
    icon: '🍼',
    subCategories: [
      { name: '奶粉', items: ['1段', '2段', '3段', '4段', '羊奶粉', '有机奶粉', '特配奶粉'] },
      { name: '尿裤湿巾', items: ['纸尿裤', '拉拉裤', '婴儿湿巾', '尿垫', '婴儿纸巾'] },
      { name: '喂养用品', items: ['奶瓶', '奶嘴', '吸奶器', '辅食机', '暖奶器', '儿童餐具'] },
      { name: '洗护用品', items: ['沐浴露', '润肤霜', '护臀霜', '爽身粉', '湿巾', '洗衣液'] },
      { name: '玩具乐器', items: ['积木', '益智玩具', '毛绒玩具', '遥控车', '乐器', '模型'] },
    ],
  },
  {
    name: '图书文娱',
    icon: '📚',
    subCategories: [
      { name: '图书', items: ['文学', '小说', '童书', '教育', '科技', '历史', '艺术'] },
      { name: '电子书', items: ['小说', '文学', '经管', '社科', '科技', '原版'] },
      { name: '音像', items: ['音乐', '影视', '教育', '纪录片', '动画片'] },
      { name: '文具', items: ['笔类', '本册', '办公文具', '画具', '学生文具', '文件夹'] },
    ],
  },
])

// 当前 hover 的分类索引
const hoveredCategoryIndex = ref(-1)

// ===== 秒杀数据 =====
interface SeckillItem {
  id: number
  name: string
  img: string
  price: number
  originalPrice: number
}

const seckillItems = ref<SeckillItem[]>([
  { id: 1, name: 'Apple iPhone 15 Pro Max 256GB', img: 'https://images.unsplash.com/photo-1696446701796-da61225697cc?w=200&h=200&fit=crop', price: 8999, originalPrice: 9999 },
  { id: 2, name: 'Sony WH-1000XM5 无线降噪耳机', img: 'https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?w=200&h=200&fit=crop', price: 1999, originalPrice: 2999 },
  { id: 3, name: 'Nintendo Switch OLED 游戏主机', img: 'https://images.unsplash.com/photo-1578303512597-81e6cc155b3e?w=200&h=200&fit=crop', price: 1899, originalPrice: 2599 },
  { id: 4, name: 'Dyson V15 Detect 无线吸尘器', img: 'https://images.unsplash.com/photo-1558317374-067fb5f30001?w=200&h=200&fit=crop', price: 3499, originalPrice: 4990 },
  { id: 5, name: '小米空气净化器 4 Pro', img: 'https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=200&h=200&fit=crop', price: 899, originalPrice: 1299 },
])

// 秒杀倒计时
const seckillHours = ref(2)
const seckillMinutes = ref(15)
const seckillSeconds = ref(30)

// ===== 热门推荐商品 =====
interface Product {
  id: number
  name: string
  img: string
  price: number
  originalPrice: number
  saleCount: number
  tag?: string
}

const hotProducts = ref<Product[]>([
  { id: 101, name: 'Apple MacBook Air M3 芯片 13.6英寸 8核CPU 8核GPU 8GB 256GB', img: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop', price: 8999, originalPrice: 10499, saleCount: 5200, tag: '热卖' },
  { id: 102, name: '戴森(Dyson) Supersonic HD15 新一代吹风机 负离子护发', img: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=300&h=300&fit=crop', price: 2590, originalPrice: 3290, saleCount: 3800, tag: '爆款' },
  { id: 103, name: 'SK-II 神仙水护肤精华露 230ml 紧致修护 补水保湿', img: 'https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=300&h=300&fit=crop', price: 1540, originalPrice: 2150, saleCount: 2900 },
  { id: 104, name: 'Nike Air Force 1 \'07 空军一号经典板鞋男女同款', img: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300&h=300&fit=crop', price: 749, originalPrice: 899, saleCount: 6100, tag: '潮流' },
  { id: 105, name: '小米14 Pro 16GB+512GB 徕卡影像 骁龙8 Gen3', img: 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300&h=300&fit=crop', price: 5499, originalPrice: 5999, saleCount: 4500 },
  { id: 106, name: '雅诗兰黛(Estee Lauder) 小棕瓶精华液 50ml 修护抗老', img: 'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=300&h=300&fit=crop', price: 935, originalPrice: 1280, saleCount: 2100 },
  { id: 107, name: '索尼(SONY) PS5 光驱版游戏主机 国行', img: 'https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?w=300&h=300&fit=crop', price: 3599, originalPrice: 3899, saleCount: 1800, tag: '新品' },
  { id: 108, name: 'Nespresso 胶囊咖啡机 Essenza Mini 全自动家用', img: 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?w=300&h=300&fit=crop', price: 866, originalPrice: 1280, saleCount: 1500 },
  { id: 109, name: '北面(The North Face) 1996 Retro Nuptse 羽绒服', img: 'https://images.unsplash.com/photo-1544022613-e87ca75a784a?w=300&h=300&fit=crop', price: 2698, originalPrice: 3398, saleCount: 980, tag: '保暖' },
  { id: 110, name: '海尔(Haier) 545升十字对开门冰箱 一级能效', img: 'https://images.unsplash.com/photo-1584568694244-14fbdf83bd30?w=300&h=300&fit=crop', price: 4299, originalPrice: 5899, saleCount: 750 },
])

// ===== 新品上架 =====
const newProducts = ref<Product[]>([
  { id: 201, name: '华为 Mate 60 Pro+ 16GB+512GB 鸿蒙系统 卫星通信', img: 'https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=300&h=300&fit=crop', price: 8999, originalPrice: 9999, saleCount: 320 },
  { id: 202, name: 'DJI Osmo Pocket 3 口袋云台相机 4K 120fps', img: 'https://images.unsplash.com/photo-1564466021188-1e17010c5352?w=300&h=300&fit=crop', price: 3499, originalPrice: 3999, saleCount: 180 },
  { id: 203, name: '科沃斯(ECOVACS) X2 Pro 扫地机器人 自动上下水', img: 'https://images.unsplash.com/photo-1588854337221-4cf9fa96059c?w=300&h=300&fit=crop', price: 4999, originalPrice: 6499, saleCount: 260 },
  { id: 204, name: 'Lululemon Align™ 女士运动瑜伽裤 高腰裸感', img: 'https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=300&h=300&fit=crop', price: 850, originalPrice: 1080, saleCount: 410 },
  { id: 205, name: 'Anker 737 240W 氮化镓充电器 三口快充', img: 'https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=300&h=300&fit=crop', price: 399, originalPrice: 599, saleCount: 580 },
  { id: 206, name: 'Philips 飞利浦 Sonicare 钻石牙刷 HX9912 智能', img: 'https://images.unsplash.com/photo-1559671088-795c52083351?w=300&h=300&fit=crop', price: 1299, originalPrice: 1899, saleCount: 230 },
  { id: 207, name: 'Bose QuietComfort Ultra 无线消噪耳机 头戴式', img: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300&h=300&fit=crop', price: 2299, originalPrice: 2999, saleCount: 170 },
  { id: 208, name: '戴森 Dyson Airwrap™ 多功能造型器 长发版', img: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=300&h=300&fit=crop', price: 3999, originalPrice: 4590, saleCount: 120 },
  { id: 209, name: 'iPad Air 6 M2芯片 11英寸 256GB WiFi版', img: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=300&h=300&fit=crop', price: 5599, originalPrice: 5999, saleCount: 290 },
  { id: 210, name: 'L\'Occitane 欧舒丹 樱花身体乳 250ml 滋润', img: 'https://images.unsplash.com/photo-1601049541289-9b1b7bbbfe19?w=300&h=300&fit=crop', price: 260, originalPrice: 380, saleCount: 650 },
])

// ===== 品牌推荐 =====
const brands = ref([
  { id: 1, name: 'Apple', logo: 'https://images.unsplash.com/photo-1621768216002-5ac171876625?w=120&h=60&fit=crop' },
  { id: 2, name: '华为', logo: 'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=120&h=60&fit=crop' },
  { id: 3, name: '小米', logo: 'https://images.unsplash.com/photo-1567581935884-3349723552ca?w=120&h=60&fit=crop' },
  { id: 4, name: 'Nike', logo: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=120&h=60&fit=crop' },
  { id: 5, name: 'Adidas', logo: 'https://images.unsplash.com/photo-1584735175315-9d5df23860e6?w=120&h=60&fit=crop' },
  { id: 6, name: 'Sony', logo: 'https://images.unsplash.com/photo-1606144042614-81e6cc155b3e?w=120&h=60&fit=crop' },
  { id: 7, name: 'Dyson', logo: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=120&h=60&fit=crop' },
  { id: 8, name: '三星', logo: 'https://images.unsplash.com/photo-1610945265064-f4d215f72119?w=120&h=60&fit=crop' },
  { id: 9, name: 'L\'Oréal', logo: 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=120&h=60&fit=crop' },
  { id: 10, name: 'Nintendo', logo: 'https://images.unsplash.com/photo-1578303512597-81e6cc155b3e?w=120&h=60&fit=crop' },
])

// ===== 导航到商品详情 =====
const goProductDetail = (id: number) => {
  router.push(`/product/${id}`)
}

// ===== 格式化价格 =====
const formatPrice = (price: number) => {
  return price.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ===== 秒杀倒计时 =====
let seckillTimer: ReturnType<typeof setInterval> | null = null
const startSeckillCountdown = () => {
  seckillTimer = setInterval(() => {
    if (seckillSeconds.value > 0) {
      seckillSeconds.value--
    } else if (seckillMinutes.value > 0) {
      seckillMinutes.value--
      seckillSeconds.value = 59
    } else if (seckillHours.value > 0) {
      seckillHours.value--
      seckillMinutes.value = 59
      seckillSeconds.value = 59
    }
  }, 1000)
}

onMounted(() => {
  startBannerAutoPlay()
  startSeckillCountdown()
})

onUnmounted(() => {
  stopBannerAutoPlay()
  if (seckillTimer) clearInterval(seckillTimer)
})
</script>

<template>
  <div class="home-page">
    <!-- ======================== 首屏区域 ======================== -->
    <section class="hero-section mb-6">
      <div class="flex h-[400px] gap-0">
        <!-- 左侧：商品分类导航 (200px) -->
        <aside
          class="w-[200px] bg-white rounded-l-xl shadow-sm flex-shrink-0 relative z-20"
          @mouseleave="hoveredCategoryIndex = -1"
        >
          <div class="py-2">
            <div
              v-for="(cat, index) in categories"
              :key="index"
              class="group/cat"
              @mouseenter="hoveredCategoryIndex = index"
            >
              <div
                :class="[
                  'flex items-center gap-2 px-4 py-[7px] text-sm cursor-pointer transition-colors',
                  hoveredCategoryIndex === index
                    ? 'bg-red-600 text-white'
                    : 'text-gray-600 hover:bg-red-50 hover:text-red-600',
                ]"
              >
                <span class="text-base">{{ cat.icon }}</span>
                <span class="font-medium truncate">{{ cat.name }}</span>
              </div>
            </div>
          </div>

          <!-- 悬浮展开的二级分类面板 -->
          <div
            v-if="hoveredCategoryIndex >= 0"
            class="absolute left-[200px] top-0 w-[680px] min-h-[400px] bg-white rounded-r-xl shadow-xl border border-gray-100 p-6 z-30"
          >
            <div class="grid grid-cols-3 gap-x-6 gap-y-5">
              <div
                v-for="(sub, sIdx) in categories[hoveredCategoryIndex].subCategories"
                :key="sIdx"
              >
                <h4 class="text-sm font-bold text-gray-900 mb-2 pb-1 border-b border-gray-100">
                  {{ sub.name }}
                </h4>
                <div class="flex flex-wrap gap-2 mt-2">
                  <button
                    v-for="(item, iIdx) in sub.items"
                    :key="iIdx"
                    class="text-xs text-gray-500 hover:text-red-600 transition-colors"
                    @click="router.push('/category')"
                  >
                    {{ item }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <!-- 右侧：轮播图 -->
        <div class="flex-1 relative overflow-hidden rounded-r-xl" @mouseenter="stopBannerAutoPlay" @mouseleave="startBannerAutoPlay">
          <!-- 轮播图片 -->
          <div
            class="flex h-full transition-transform duration-500 ease-out"
            :style="{ transform: `translateX(-${currentBanner * 100}%)` }"
          >
            <div
              v-for="banner in banners"
              :key="banner.id"
              class="w-full h-full flex-shrink-0 relative cursor-pointer"
              @click="router.push('/search')"
            >
              <img
                :src="banner.img"
                :alt="banner.title"
                class="w-full h-full object-cover"
              />
              <!-- 文字遮罩 -->
              <div class="absolute inset-0 bg-gradient-to-r from-black/40 via-transparent to-transparent" />
              <div class="absolute left-8 top-1/2 -translate-y-1/2 text-white">
                <h2 class="text-3xl font-bold mb-2 drop-shadow-lg">{{ banner.title }}</h2>
                <p class="text-lg opacity-90 drop-shadow">{{ banner.subtitle }}</p>
              </div>
            </div>
          </div>

          <!-- 左右切换按钮 -->
          <button
            class="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 bg-black/30 hover:bg-black/50 text-white rounded-full flex items-center justify-center transition-colors backdrop-blur-sm"
            @click="goToBanner((currentBanner - 1 + banners.length) % banners.length)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            class="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 bg-black/30 hover:bg-black/50 text-white rounded-full flex items-center justify-center transition-colors backdrop-blur-sm"
            @click="goToBanner((currentBanner + 1) % banners.length)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <!-- 底部指示器 -->
          <div class="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2">
            <button
              v-for="(_, index) in banners"
              :key="index"
              :class="[
                'h-2 rounded-full transition-all duration-300',
                currentBanner === index ? 'w-6 bg-white' : 'w-2 bg-white/50 hover:bg-white/70',
              ]"
              @click="goToBanner(index)"
            />
          </div>
        </div>
      </div>
    </section>

    <!-- ======================== 秒杀专区 ======================== -->
    <section class="seckill-section mb-6">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <!-- 头部 -->
        <div class="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-red-600 to-red-500">
          <div class="flex items-center gap-4">
            <h2 class="text-xl font-bold text-white">限时秒杀</h2>
            <div class="flex items-center gap-1 text-white">
              <span class="text-sm">距结束</span>
              <div class="flex items-center gap-1">
                <span class="w-7 h-7 bg-black/20 rounded text-center leading-7 text-sm font-mono font-bold">{{ String(seckillHours).padStart(2, '0') }}</span>
                <span class="text-xs">:</span>
                <span class="w-7 h-7 bg-black/20 rounded text-center leading-7 text-sm font-mono font-bold">{{ String(seckillMinutes).padStart(2, '0') }}</span>
                <span class="text-xs">:</span>
                <span class="w-7 h-7 bg-black/20 rounded text-center leading-7 text-sm font-mono font-bold">{{ String(seckillSeconds).padStart(2, '0') }}</span>
              </div>
            </div>
          </div>
          <button class="text-sm text-white/90 hover:text-white flex items-center gap-1 transition-colors" @click="router.push('/hot')">
            查看全部
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <!-- 秒杀商品横向滚动 -->
        <div class="flex gap-4 p-5 overflow-x-auto">
          <button
            v-for="item in seckillItems"
            :key="item.id"
            class="flex-shrink-0 w-[200px] group text-left"
            @click="goProductDetail(item.id)"
          >
            <div class="aspect-square rounded-lg bg-gray-50 overflow-hidden mb-2">
              <img :src="item.img" :alt="item.name" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
            </div>
            <p class="text-xs text-gray-700 line-clamp-2 mb-2 h-8 leading-4">{{ item.name }}</p>
            <div class="flex items-baseline gap-2">
              <span class="text-red-600 font-bold text-base">&yen;{{ item.price }}</span>
              <span class="text-gray-400 text-xs line-through">&yen;{{ item.originalPrice }}</span>
            </div>
          </button>
        </div>
      </div>
    </section>

    <!-- ======================== 品牌推荐 ======================== -->
    <section class="brand-section mb-6">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-bold text-gray-900">热门品牌</h2>
          <button class="text-sm text-gray-500 hover:text-red-600 transition-colors" @click="router.push('/brand')">查看全部 &rarr;</button>
        </div>
        <div class="grid grid-cols-10 gap-3">
          <button
            v-for="brand in brands"
            :key="brand.id"
            class="group flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-100 hover:border-red-200 hover:shadow-md transition-all"
            @click="router.push(`/brand/${brand.id}`)"
          >
            <div class="w-12 h-12 rounded-full bg-gray-50 overflow-hidden flex items-center justify-center">
              <img :src="brand.logo" :alt="brand.name" class="w-full h-full object-cover group-hover:scale-110 transition-transform" />
            </div>
            <span class="text-xs text-gray-600 truncate w-full text-center">{{ brand.name }}</span>
          </button>
        </div>
      </div>
    </section>

    <!-- ======================== 热门推荐 ======================== -->
    <section class="hot-section mb-6">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <!-- 区块头部 -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div class="flex items-center gap-3">
            <div class="w-1 h-5 bg-red-600 rounded-full" />
            <h2 class="text-lg font-bold text-gray-900">热门推荐</h2>
            <span class="text-xs text-gray-400">精选好物，品质保障</span>
          </div>
          <button class="text-sm text-gray-500 hover:text-red-600 transition-colors" @click="router.push('/hot')">查看更多 &rarr;</button>
        </div>

        <!-- 商品网格 5列 -->
        <div class="p-5 grid grid-cols-5 gap-4">
          <button
            v-for="product in hotProducts"
            :key="product.id"
            class="group text-left bg-white rounded-lg border border-gray-100 hover:border-red-100 hover:-translate-y-1 hover:shadow-lg transition-all duration-300 overflow-hidden"
            @click="goProductDetail(product.id)"
          >
            <!-- 商品图片 -->
            <div class="aspect-square bg-gray-50 overflow-hidden relative">
              <img
                :src="product.img"
                :alt="product.name"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              />
              <!-- 标签 -->
              <span
                v-if="product.tag"
                class="absolute top-2 left-2 bg-red-600 text-white text-[10px] px-2 py-0.5 rounded font-medium"
              >
                {{ product.tag }}
              </span>
            </div>
            <!-- 商品信息 -->
            <div class="p-3">
              <!-- 名称：两行，超出省略 -->
              <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">
                {{ product.name }}
              </p>
              <!-- 价格 -->
              <div class="flex items-baseline gap-2">
                <span class="text-red-600 font-bold text-base">
                  <span class="text-xs">&yen;</span>{{ Math.floor(product.price) }}<span class="text-xs">.{{ String((product.price % 1).toFixed(2)).split('.')[1] }}</span>
                </span>
                <span class="text-gray-400 text-xs line-through">&yen;{{ product.originalPrice }}</span>
              </div>
              <!-- 销量 -->
              <p class="text-xs text-gray-400 mt-1">已售 {{ product.saleCount >= 1000 ? (product.saleCount / 1000).toFixed(1) + '万' : product.saleCount }}</p>
            </div>
          </button>
        </div>
      </div>
    </section>

    <!-- ======================== 新品上架 ======================== -->
    <section class="new-section mb-6">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <!-- 区块头部 -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div class="flex items-center gap-3">
            <div class="w-1 h-5 bg-green-500 rounded-full" />
            <h2 class="text-lg font-bold text-gray-900">新品上架</h2>
            <span class="text-xs text-gray-400">新鲜好物，抢先体验</span>
          </div>
          <button class="text-sm text-gray-500 hover:text-red-600 transition-colors" @click="router.push('/new')">查看更多 &rarr;</button>
        </div>

        <!-- 商品网格 5列 -->
        <div class="p-5 grid grid-cols-5 gap-4">
          <button
            v-for="product in newProducts"
            :key="product.id"
            class="group text-left bg-white rounded-lg border border-gray-100 hover:border-green-200 hover:-translate-y-1 hover:shadow-lg transition-all duration-300 overflow-hidden"
            @click="goProductDetail(product.id)"
          >
            <!-- 商品图片 -->
            <div class="aspect-square bg-gray-50 overflow-hidden relative">
              <img
                :src="product.img"
                :alt="product.name"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              />
              <!-- NEW 标签 -->
              <span class="absolute top-2 left-2 bg-green-500 text-white text-[10px] px-2 py-0.5 rounded font-medium">
                NEW
              </span>
            </div>
            <!-- 商品信息 -->
            <div class="p-3">
              <!-- 名称：两行，超出省略 -->
              <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-green-600 transition-colors">
                {{ product.name }}
              </p>
              <!-- 价格 -->
              <div class="flex items-baseline gap-2">
                <span class="text-red-600 font-bold text-base">
                  <span class="text-xs">&yen;</span>{{ Math.floor(product.price) }}<span class="text-xs">.{{ String((product.price % 1).toFixed(2)).split('.')[1] }}</span>
                </span>
                <span class="text-gray-400 text-xs line-through">&yen;{{ product.originalPrice }}</span>
              </div>
              <!-- 销量 -->
              <p class="text-xs text-gray-400 mt-1">已售 {{ product.saleCount }}</p>
            </div>
          </button>
        </div>
      </div>
    </section>

    <!-- ======================== 为你推荐 ======================== -->
    <section class="recommend-section">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <!-- 区块头部 -->
        <div class="flex items-center justify-center px-6 py-4 border-b border-gray-100">
          <div class="flex items-center gap-3">
            <div class="w-8 h-px bg-gray-200" />
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            <h2 class="text-lg font-bold text-gray-900">为你推荐</h2>
            <div class="w-8 h-px bg-gray-200" />
          </div>
        </div>

        <!-- 商品网格 5列 -->
        <div class="p-5 grid grid-cols-5 gap-4">
          <button
            v-for="product in [...hotProducts, ...newProducts].slice(0, 10)"
            :key="`rec-${product.id}`"
            class="group text-left bg-white rounded-lg border border-gray-100 hover:border-red-100 hover:-translate-y-1 hover:shadow-lg transition-all duration-300 overflow-hidden"
            @click="goProductDetail(product.id)"
          >
            <!-- 商品图片 -->
            <div class="aspect-square bg-gray-50 overflow-hidden relative">
              <img
                :src="product.img"
                :alt="product.name"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              />
            </div>
            <!-- 商品信息 -->
            <div class="p-3">
              <p class="text-sm text-gray-800 line-clamp-2 leading-5 min-h-[40px] mb-2 group-hover:text-red-600 transition-colors">
                {{ product.name }}
              </p>
              <div class="flex items-baseline gap-2">
                <span class="text-red-600 font-bold text-base">
                  <span class="text-xs">&yen;</span>{{ Math.floor(product.price) }}<span class="text-xs">.00</span>
                </span>
              </div>
            </div>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* 自定义滚动条隐藏 */
.overflow-x-auto::-webkit-scrollbar {
  display: none;
}
.overflow-x-auto {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
