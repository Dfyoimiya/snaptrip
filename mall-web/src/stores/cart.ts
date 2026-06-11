/**
 * ============================================
 * 购物车状态管理 (Pinia Store)
 * PC 端专用：所有计算逻辑在前端实时响应
 * ============================================
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { CartItem } from '@/types/cart'

export const useCartStore = defineStore(
  'cart',
  () => {
    // ===== State =====
    /** 购物车列表 */
    const cartList = ref<CartItem[]>([])
    /** 加载状态 */
    const loading = ref(false)

    // ===== Getters =====
    /** 购物车商品总数（所有商品数量之和） */
    const totalCount = computed(() =>
      cartList.value.reduce((sum, item) => sum + item.quantity, 0),
    )
    /** 选中商品总数 */
    const checkedCount = computed(() =>
      cartList.value
        .filter((item) => item.checked)
        .reduce((sum, item) => sum + item.quantity, 0),
    )
    /** 选中商品总价（不含优惠） */
    const checkedTotalPrice = computed(() =>
      cartList.value
        .filter((item) => item.checked)
        .reduce((sum, item) => sum + item.price * item.quantity, 0),
    )
    /** 选中商品原价总计 */
    const checkedOriginalPrice = computed(() =>
      cartList.value
        .filter((item) => item.checked)
        .reduce((sum, item) => sum + (item.originalPrice || item.price) * item.quantity, 0),
    )
    /** 优惠金额 */
    const checkedDiscount = computed(() =>
      checkedOriginalPrice.value - checkedTotalPrice.value,
    )
    /** 是否全选 */
    const isAllChecked = computed(
      () => cartList.value.length > 0 && cartList.value.every((item) => item.checked),
    )
    /** 是否有商品 */
    const hasItems = computed(() => cartList.value.length > 0)
    /** 是否有选中 */
    const hasChecked = computed(() => cartList.value.some((item) => item.checked))

    // ===== Actions =====
    /**
     * 获取购物车列表（Mock 数据填充）
     */
    const fetchCartList = async () => {
      loading.value = true
      try {
        // 模拟 API 延迟
        await new Promise((resolve) => setTimeout(resolve, 300))
        // Mock 数据
        cartList.value = getMockCartItems()
      } finally {
        loading.value = false
      }
    }

    /**
     * 更新商品数量（前端实时 + 后端同步）
     */
    const updateQuantity = async (id: string, quantity: number) => {
      if (quantity < 1) return
      const target = cartList.value.find((item) => item.id === id)
      if (!target) return
      // 限制最大数量
      const finalQty = Math.min(quantity, 99)
      target.quantity = finalQty
    }

    /**
     * 删除单个商品
     */
    const removeItem = async (id: string) => {
      cartList.value = cartList.value.filter((item) => item.id !== id)
    }

    /**
     * 批量删除选中商品
     */
    const removeChecked = async () => {
      cartList.value = cartList.value.filter((item) => !item.checked)
    }

    /**
     * 切换商品选中状态
     */
    const toggleCheck = (id: string) => {
      const target = cartList.value.find((item) => item.id === id)
      if (target) {
        target.checked = !target.checked
      }
    }

    /**
     * 全选 / 取消全选
     */
    const toggleCheckAll = (checked: boolean) => {
      cartList.value.forEach((item) => {
        item.checked = checked
      })
    }

    /**
     * 清空购物车
     */
    const clearCart = () => {
      cartList.value = []
    }

    return {
      cartList,
      loading,
      totalCount,
      checkedCount,
      checkedTotalPrice,
      checkedOriginalPrice,
      checkedDiscount,
      isAllChecked,
      hasItems,
      hasChecked,
      fetchCartList,
      updateQuantity,
      removeItem,
      removeChecked,
      toggleCheck,
      toggleCheckAll,
      clearCart,
    }
  },
  {
    persist: true,
  },
)

/**
 * Mock 购物车数据
 */
function getMockCartItems(): CartItem[] {
  return [
    {
      id: '1001',
      memberId: '1',
      memberNickname: '用户9527',
      productId: 101,
      productSkuId: 1003,
      productSkuCode: '午夜色 M3-10C-16G-512G',
      productCategoryId: 19,
      productName: 'Apple MacBook Air 13.6英寸 M3芯片 8核CPU 10核GPU 16GB+512GB',
      productSubTitle: 'Apple M3 芯片，18小时续航，轻薄便携',
      productBrand: 'Apple',
      productPic: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=200&h=200&fit=crop',
      price: 9999,
      originalPrice: 11999,
      quantity: 1,
      productAttr: '{"颜色":"午夜色","芯片":"M3-10C","内存":"16GB","硬盘":"512GB"}',
      productSn: 'APPLE-MBA-M3-2024',
      createDate: '2026-06-01',
      modifyDate: '2026-06-08',
      deleteStatus: 0,
      checked: true,
      spDataStr: '午夜色，16GB+512GB',
    },
    {
      id: '1002',
      memberId: '1',
      memberNickname: '用户9527',
      productId: 102,
      productSkuId: 2001,
      productSkuCode: 'HD15-镍灰色',
      productCategoryId: 20,
      productName: '戴森(Dyson) Supersonic HD15 新一代吹风机 负离子护发',
      productSubTitle: '快速干发，不伤发质，智能温控',
      productBrand: 'Dyson',
      productPic: 'https://images.unsplash.com/photo-1522338140262-f46f5913618a?w=200&h=200&fit=crop',
      price: 2590,
      originalPrice: 3290,
      quantity: 1,
      productAttr: '{"颜色":"镍灰色"}',
      productSn: 'DYSON-HD15-2024',
      createDate: '2026-06-02',
      modifyDate: '2026-06-08',
      deleteStatus: 0,
      checked: true,
      spDataStr: '镍灰色',
    },
    {
      id: '1003',
      memberId: '1',
      memberNickname: '用户9527',
      productId: 103,
      productSkuId: 3001,
      productSkuCode: 'SK-II-230ml',
      productCategoryId: 28,
      productName: 'SK-II 神仙水护肤精华露 230ml 紧致修护 补水保湿',
      productSubTitle: 'PITERA 精华，焕活肌肤',
      productBrand: 'SK-II',
      productPic: 'https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=200&h=200&fit=crop',
      price: 1540,
      originalPrice: 2150,
      quantity: 2,
      productAttr: '{"规格":"230ml"}',
      productSn: 'SKII-ESSENCE-230',
      createDate: '2026-06-03',
      modifyDate: '2026-06-08',
      deleteStatus: 0,
      checked: false,
      spDataStr: '230ml 标准装',
    },
    {
      id: '1004',
      memberId: '1',
      memberNickname: '用户9527',
      productId: 104,
      productSkuId: 4001,
      productSkuCode: 'AF1-WHITE-42',
      productCategoryId: 34,
      productName: 'Nike Air Force 1 \'07 空军一号经典板鞋男女同款',
      productSubTitle: '经典百搭，舒适耐穿',
      productBrand: 'Nike',
      productPic: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=200&h=200&fit=crop',
      price: 749,
      originalPrice: 899,
      quantity: 1,
      productAttr: '{"颜色":"白色","尺码":"42"}',
      productSn: 'NIKE-AF1-2024',
      createDate: '2026-06-04',
      modifyDate: '2026-06-08',
      deleteStatus: 0,
      checked: true,
      spDataStr: '白色，42码',
    },
    {
      id: '1005',
      memberId: '1',
      memberNickname: '用户9527',
      productId: 105,
      productSkuId: 5001,
      productSkuCode: 'XM14-16G-512G-BLACK',
      productCategoryId: 19,
      productName: '小米14 Pro 16GB+512GB 徕卡影像 骁龙8 Gen3',
      productSubTitle: '徕卡光学 Summilux 镜头，骁龙8 Gen3',
      productBrand: '小米',
      productPic: 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=200&h=200&fit=crop',
      price: 5499,
      originalPrice: 5999,
      quantity: 1,
      productAttr: '{"颜色":"黑色","内存":"16GB","硬盘":"512GB"}',
      productSn: 'XIAOMI-14PRO-2024',
      createDate: '2026-06-05',
      modifyDate: '2026-06-08',
      deleteStatus: 0,
      checked: false,
      spDataStr: '黑色，16GB+512GB',
    },
  ]
}
