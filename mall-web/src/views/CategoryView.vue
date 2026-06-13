<script setup lang="ts">
/**
 * ============================================
 * 全部分类页 (CategoryView)
 * PC 端平铺式多级分类面板
 * 类似京东全部分类页面，一级分类横向 tab + 二级/三级分类平铺展示
 * ============================================
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

/** 分类数据结构 */
interface SubCategory {
  id: number
  name: string
  icon?: string
}

interface CategoryGroup {
  id: number
  name: string
  icon: string
  banner?: string
  children: {
    name: string
    items: SubCategory[]
  }[]
}

/** Mock 分类数据（平铺式多级结构） */
const categoryGroups = ref<CategoryGroup[]>([
  {
    id: 1, name: '手机数码', icon: '📱',
    children: [
      { name: '手机通讯', items: [{id: 101, name: '5G手机'}, {id: 102, name: '游戏手机'}, {id: 103, name: '拍照手机'}, {id: 104, name: '全面屏手机'}, {id: 105, name: '对讲机'}] },
      { name: '手机配件', items: [{id: 111, name: '手机壳'}, {id: 112, name: '贴膜'}, {id: 113, name: '移动电源'}, {id: 114, name: '数据线'}, {id: 115, name: '充电器'}, {id: 116, name: '手机存储卡'}] },
      { name: '摄影摄像', items: [{id: 121, name: '数码相机'}, {id: 122, name: '微单相机'}, {id: 123, name: '单反相机'}, {id: 124, name: '运动相机'}, {id: 125, name: '摄像机'}, {id: 126, name: '镜头'}] },
      { name: '数码配件', items: [{id: 131, name: '存储卡'}, {id: 132, name: '读卡器'}, {id: 133, name: '三脚架'}, {id: 134, name: '相机包'}, {id: 135, name: '滤镜'}, {id: 136, name: '电池/充电器'}] },
      { name: '智能设备', items: [{id: 141, name: '智能手表'}, {id: 142, name: '智能手环'}, {id: 143, name: 'VR眼镜'}, {id: 144, name: '无人机'}, {id: 145, name: '智能机器人'}] },
    ],
  },
  {
    id: 2, name: '电脑办公', icon: '💻',
    children: [
      { name: '电脑整机', items: [{id: 201, name: '轻薄本'}, {id: 202, name: '游戏本'}, {id: 203, name: '台式机'}, {id: 204, name: '一体机'}, {id: 205, name: '平板电脑'}, {id: 206, name: '服务器'}] },
      { name: '电脑配件', items: [{id: 211, name: '显示器'}, {id: 212, name: 'CPU'}, {id: 213, name: '主板'}, {id: 214, name: '显卡'}, {id: 215, name: '硬盘'}, {id: 216, name: '内存'}, {id: 217, name: '机箱'}, {id: 218, name: '电源'}] },
      { name: '外设产品', items: [{id: 221, name: '鼠标'}, {id: 222, name: '键盘'}, {id: 223, name: 'U盘'}, {id: 224, name: '移动硬盘'}, {id: 225, name: '鼠标垫'}, {id: 226, name: '摄像头'}] },
      { name: '办公设备', items: [{id: 231, name: '投影机'}, {id: 232, name: '打印机'}, {id: 233, name: '碎纸机'}, {id: 234, name: '考勤机'}, {id: 235, name: '保险柜'}, {id: 236, name: '白板'}] },
      { name: '网络设备', items: [{id: 241, name: '路由器'}, {id: 242, name: '交换机'}, {id: 243, name: '网卡'}, {id: 244, name: '网络存储'}, {id: 245, name: '光纤设备'}] },
    ],
  },
  {
    id: 3, name: '家用电器', icon: '🏠',
    children: [
      { name: '电视', items: [{id: 301, name: '超薄电视'}, {id: 302, name: '全面屏'}, {id: 303, name: '4K超清'}, {id: 304, name: 'OLED电视'}, {id: 305, name: '智能电视'}, {id: 306, name: '激光电视'}] },
      { name: '空调', items: [{id: 311, name: '壁挂式'}, {id: 312, name: '柜机'}, {id: 313, name: '中央空调'}, {id: 314, name: '移动空调'}, {id: 315, name: '变频空调'}] },
      { name: '冰箱', items: [{id: 321, name: '对开门'}, {id: 322, name: '三门'}, {id: 323, name: '双门'}, {id: 324, name: '冷柜/冰吧'}, {id: 325, name: '多门'}] },
      { name: '洗衣机', items: [{id: 331, name: '滚筒'}, {id: 332, name: '洗烘一体'}, {id: 333, name: '波轮'}, {id: 334, name: '迷你洗衣机'}, {id: 335, name: '烘干机'}] },
      { name: '厨卫大电', items: [{id: 341, name: '油烟机'}, {id: 342, name: '燃气灶'}, {id: 343, name: '洗碗机'}, {id: 344, name: '电热水器'}, {id: 345, name: '燃气热水器'}, {id: 346, name: '消毒柜'}] },
      { name: '生活电器', items: [{id: 351, name: '空气净化器'}, {id: 352, name: '加湿器'}, {id: 353, name: '吸尘器'}, {id: 354, name: '扫地机器人'}, {id: 355, name: '电风扇'}, {id: 356, name: '除湿机'}] },
    ],
  },
  {
    id: 4, name: '家居家装', icon: '🛋️',
    children: [
      { name: '家纺', items: [{id: 401, name: '床品套件'}, {id: 402, name: '被子'}, {id: 403, name: '枕头'}, {id: 404, name: '蚊帐'}, {id: 405, name: '凉席'}, {id: 406, name: '毛巾浴巾'}] },
      { name: '灯具', items: [{id: 411, name: '吸顶灯'}, {id: 412, name: '吊灯'}, {id: 413, name: '台灯'}, {id: 414, name: '筒灯射灯'}, {id: 415, name: '灯带'}, {id: 416, name: '户外灯'}] },
      { name: '家具', items: [{id: 421, name: '沙发'}, {id: 422, name: '床'}, {id: 423, name: '床垫'}, {id: 424, name: '餐桌'}, {id: 425, name: '衣柜'}, {id: 426, name: '茶几'}, {id: 427, name: '鞋柜'}] },
      { name: '厨具', items: [{id: 431, name: '炒锅'}, {id: 432, name: '压力锅'}, {id: 433, name: '蒸锅'}, {id: 434, name: '煎锅'}, {id: 435, name: '汤锅'}, {id: 436, name: '奶锅'}] },
      { name: '卫浴', items: [{id: 441, name: '马桶'}, {id: 442, name: '浴室柜'}, {id: 443, name: '花洒'}, {id: 444, name: '水龙头'}, {id: 445, name: '浴缸'}, {id: 446, name: '地漏'}] },
    ],
  },
  {
    id: 5, name: '服装服饰', icon: '👗',
    children: [
      { name: '女装', items: [{id: 501, name: '连衣裙'}, {id: 502, name: 'T恤'}, {id: 503, name: '衬衫'}, {id: 504, name: '卫衣'}, {id: 505, name: '外套'}, {id: 506, name: '牛仔裤'}, {id: 507, name: '半身裙'}] },
      { name: '男装', items: [{id: 511, name: 'T恤'}, {id: 512, name: '衬衫'}, {id: 513, name: 'POLO衫'}, {id: 514, name: '夹克'}, {id: 515, name: '西服'}, {id: 516, name: '休闲裤'}, {id: 517, name: '牛仔裤'}] },
      { name: '童装', items: [{id: 521, name: '套装'}, {id: 522, name: '上衣'}, {id: 523, name: '裤子'}, {id: 524, name: '裙子'}, {id: 525, name: '亲子装'}] },
      { name: '内衣', items: [{id: 531, name: '文胸'}, {id: 532, name: '内裤'}, {id: 533, name: '睡衣'}, {id: 534, name: '保暖内衣'}, {id: 535, name: '袜子'}] },
      { name: '配饰', items: [{id: 541, name: '围巾'}, {id: 542, name: '帽子'}, {id: 543, name: '手套'}, {id: 544, name: '皮带'}, {id: 545, name: '太阳镜'}] },
    ],
  },
  {
    id: 6, name: '美妆个护', icon: '💄',
    children: [
      { name: '面部护肤', items: [{id: 601, name: '洁面'}, {id: 602, name: '爽肤水'}, {id: 603, name: '乳液/面霜'}, {id: 604, name: '精华'}, {id: 605, name: '面膜'}, {id: 606, name: '防晒'}, {id: 607, name: '眼霜'}] },
      { name: '彩妆香氛', items: [{id: 611, name: '口红'}, {id: 612, name: '粉底'}, {id: 613, name: '眼影'}, {id: 614, name: '香水'}, {id: 615, name: '眉笔'}, {id: 616, name: '腮红'}] },
      { name: '美发护发', items: [{id: 621, name: '洗发水'}, {id: 622, name: '护发素'}, {id: 623, name: '染发'}, {id: 624, name: '造型'}, {id: 625, name: '发膜'}] },
      { name: '身体护理', items: [{id: 631, name: '沐浴露'}, {id: 632, name: '身体乳'}, {id: 633, name: '护手霜'}, {id: 634, name: '剃须'}, {id: 635, name: '脱毛'}] },
      { name: '口腔护理', items: [{id: 641, name: '牙膏'}, {id: 642, name: '牙刷'}, {id: 643, name: '漱口水'}, {id: 644, name: '电动牙刷'}] },
    ],
  },
  {
    id: 7, name: '运动户外', icon: '⚽',
    children: [
      { name: '运动鞋包', items: [{id: 701, name: '跑步鞋'}, {id: 702, name: '休闲鞋'}, {id: 703, name: '篮球鞋'}, {id: 704, name: '足球鞋'}, {id: 705, name: '板鞋'}, {id: 706, name: '运动包'}] },
      { name: '运动服饰', items: [{id: 711, name: '运动T恤'}, {id: 712, name: '运动裤'}, {id: 713, name: '卫衣'}, {id: 714, name: '夹克'}, {id: 715, name: '运动套装'}, {id: 716, name: '健身服'}] },
      { name: '健身训练', items: [{id: 721, name: '跑步机'}, {id: 722, name: '动感单车'}, {id: 723, name: '哑铃'}, {id: 724, name: '瑜伽垫'}, {id: 725, name: '健腹轮'}] },
      { name: '户外装备', items: [{id: 731, name: '帐篷'}, {id: 732, name: '背包'}, {id: 733, name: '睡袋'}, {id: 734, name: '登山鞋'}, {id: 735, name: '冲锋衣'}] },
      { name: '体育用品', items: [{id: 741, name: '乒乓球'}, {id: 742, name: '羽毛球'}, {id: 743, name: '篮球'}, {id: 744, name: '足球'}, {id: 745, name: '网球'}] },
    ],
  },
  {
    id: 8, name: '食品生鲜', icon: '🍎',
    children: [
      { name: '新鲜水果', items: [{id: 801, name: '苹果'}, {id: 802, name: '橙子'}, {id: 803, name: '芒果'}, {id: 804, name: '葡萄'}, {id: 805, name: '车厘子'}, {id: 806, name: '榴莲'}] },
      { name: '海鲜水产', items: [{id: 811, name: '虾类'}, {id: 812, name: '鱼类'}, {id: 813, name: '蟹类'}, {id: 814, name: '贝类'}, {id: 815, name: '海参'}] },
      { name: '肉禽蛋品', items: [{id: 821, name: '牛肉'}, {id: 822, name: '猪肉'}, {id: 823, name: '羊肉'}, {id: 824, name: '鸡肉'}, {id: 825, name: '鸡蛋'}, {id: 826, name: '牛排'}] },
      { name: '粮油调味', items: [{id: 831, name: '大米'}, {id: 832, name: '食用油'}, {id: 833, name: '面粉'}, {id: 834, name: '酱油'}, {id: 835, name: '调味酱'}] },
      { name: '休闲食品', items: [{id: 841, name: '坚果'}, {id: 842, name: '饼干'}, {id: 843, name: '巧克力'}, {id: 844, name: '糖果'}, {id: 845, name: '肉干'}, {id: 846, name: '薯片'}] },
    ],
  },
])

/** 当前激活的一级分类 */
const activeTab = ref(0)

/** 当前展示的分类组 */
const currentGroup = computed(() => categoryGroups.value[activeTab.value])

/** 点击分类跳转到搜索 */
const goSearch = (catName: string) => {
  router.push({
    path: '/search',
    query: { keyword: catName, categoryId: String(currentGroup.value.id) },
  })
}

/** 快捷入口 */
const quickLinks = [
  { label: '手机', query: '手机' },
  { label: '电脑', query: '电脑' },
  { label: '空调', query: '空调' },
  { label: '电视', query: '电视' },
  { label: '冰箱', query: '冰箱' },
  { label: '洗衣机', query: '洗衣机' },
  { label: '运动鞋', query: '运动鞋' },
  { label: '美妆', query: '美妆' },
]
</script>

<template>
  <div class="category-page space-y-5">
    <!-- ====== 顶部快捷入口 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h2 class="text-base font-bold text-gray-900 mb-3">热门分类</h2>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="link in quickLinks"
          :key="link.label"
          class="px-4 py-2 bg-gray-50 rounded-lg text-sm text-gray-700 hover:bg-red-50 hover:text-red-600 transition-colors"
          @click="goSearch(link.query)"
        >
          {{ link.label }}
        </button>
      </div>
    </div>

    <!-- ====== 一级分类 Tab 导航 ====== -->
    <div class="bg-white rounded-t-xl shadow-sm border border-gray-100 border-b-0">
      <div class="flex overflow-x-auto">
        <button
          v-for="(cat, index) in categoryGroups"
          :key="cat.id"
          :class="[
            'flex-shrink-0 px-6 py-4 text-sm font-medium transition-colors border-b-2 whitespace-nowrap',
            activeTab === index
              ? 'text-red-600 border-red-600 bg-red-50/50'
              : 'text-gray-600 border-transparent hover:text-gray-900 hover:bg-gray-50',
          ]"
          @click="activeTab = index"
        >
          <span class="mr-1.5">{{ cat.icon }}</span>
          {{ cat.name }}
        </button>
      </div>
    </div>

    <!-- ====== 二级/三级分类平铺面板 ====== -->
    <div class="bg-white rounded-b-xl shadow-sm border border-gray-100 border-t-0 p-6">
      <div class="mb-4 pb-3 border-b border-gray-100">
        <h3 class="text-lg font-bold text-gray-900 flex items-center gap-2">
          <span class="text-xl">{{ currentGroup.icon }}</span>
          {{ currentGroup.name }}
          <span class="text-xs font-normal text-gray-400 ml-2">共 {{ currentGroup.children.reduce((s, c) => s + c.items.length, 0) }} 个细分品类</span>
        </h3>
      </div>

      <div class="space-y-6">
        <div
          v-for="(group, gIdx) in currentGroup.children"
          :key="gIdx"
          class="flex items-start gap-4"
        >
          <!-- 二级分类标题 -->
          <div class="w-24 flex-shrink-0 pt-2">
            <span class="text-sm font-bold text-gray-800">{{ group.name }}</span>
          </div>

          <!-- 三级分类标签云 -->
          <div class="flex-1 flex flex-wrap gap-2">
            <button
              v-for="item in group.items"
              :key="item.id"
              class="px-3 py-1.5 text-sm text-gray-600 bg-gray-50 rounded-md hover:bg-red-50 hover:text-red-600 transition-colors"
              @click="goSearch(item.name)"
            >
              {{ item.name }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== 全部品牌快捷入口 ====== -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-base font-bold text-gray-900">热门品牌</h3>
        <button class="text-sm text-gray-500 hover:text-red-600" @click="router.push('/brand')">
          查看全部 &rarr;
        </button>
      </div>
      <div class="grid grid-cols-10 gap-3">
        <button
          v-for="brand in ['Apple','华为','小米','Nike','Adidas','Sony','Dyson','三星','联想','海尔']"
          :key="brand"
          class="flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-100 hover:border-red-200 hover:shadow-sm transition-all"
          @click="router.push('/brand')"
        >
          <div class="w-10 h-10 rounded-full bg-gray-50 flex items-center justify-center text-xs font-bold text-gray-400">
            {{ brand.charAt(0) }}
          </div>
          <span class="text-xs text-gray-600">{{ brand }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
