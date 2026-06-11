<script setup lang="ts">
/**
 * ============================================
 * 公告详情页 (NoticeDetailView)
 * ============================================
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const noticeId = Number(route.params.id)

const notices = [
  { id: 1, title: '关于618年中大促活动规则调整的通知', category: '活动公告', publishTime: '2026-06-08', content: '尊敬的各位用户：\n\n为更好地服务广大消费者，现对618年中大促部分活动规则进行调整，具体内容如下：\n\n一、活动时间\n2026年6月10日00:00:00 - 2026年6月18日23:59:59\n\n二、满减规则\n1. 满299减30\n2. 满599减80\n3. 满999减150\n4. 满1999减400\n5. 满4999减1000\n\n三、优惠券使用规则\n1. 优惠券可与满减活动叠加使用\n2. 每个订单最多使用3张优惠券\n3. 部分特殊商品不参与优惠活动\n\n四、其他说明\n1. 活动期间订单量较大，发货时间可能延长1-2天\n2. 如对活动有任何疑问，请联系在线客服\n\n感谢您的理解与支持！' },
  { id: 2, title: '物流配送时效调整公告', category: '服务公告', publishTime: '2026-06-07', content: '尊敬的各位用户：\n\n因受近期恶劣天气影响，部分地区的物流配送时效将有所调整。\n\n受影响地区：\n- 华南地区：预计延迟1-2天\n- 华东地区：预计延迟0.5-1天\n- 其他地区：正常配送\n\n我们会密切关注天气变化，尽最大努力保障您的包裹及时送达。给您带来不便敬请谅解！' },
  { id: 3, title: '新增支付方式——微信支付上线', category: '功能更新', publishTime: '2026-06-06', content: '亲爱的用户：\n\n商城已正式上线微信支付功能！\n\n支持以下支付方式：\n1. 微信扫码支付\n2. 微信H5支付\n3. 微信支付分（先用后付）\n\n使用微信支付可享受专属优惠，首单立减10元！' },
]

const notice = ref(notices.find(n => n.id === noticeId) || notices[0])
</script>

<template>
  <div class="notice-detail-page max-w-3xl mx-auto">
    <!-- 面包屑 -->
    <nav class="flex items-center gap-2 text-sm text-gray-500 mb-4">
      <button class="hover:text-red-600" @click="router.push('/notice')">商城公告</button>
      <span class="text-gray-300">/</span>
      <span class="text-gray-900">详情</span>
    </nav>

    <!-- 详情卡片 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
      <!-- 标题区 -->
      <div class="text-center mb-6 pb-6 border-b border-gray-100">
        <h1 class="text-xl font-bold text-gray-900 mb-3">{{ notice.title }}</h1>
        <div class="flex items-center justify-center gap-3 text-sm text-gray-400">
          <span class="bg-gray-100 text-gray-500 px-2 py-0.5 rounded text-xs">{{ notice.category }}</span>
          <span>{{ notice.publishTime }}</span>
        </div>
      </div>

      <!-- 正文 -->
      <div class="prose prose-sm max-w-none text-gray-700 leading-relaxed whitespace-pre-line">
        {{ notice.content }}
      </div>

      <!-- 底部 -->
      <div class="mt-8 pt-6 border-t border-gray-100 flex items-center justify-between">
        <button class="text-sm text-gray-500 hover:text-red-600 flex items-center gap-1" @click="router.push('/notice')">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          返回列表
        </button>
        <span class="text-xs text-gray-400">Mall PC Web 商城运营团队</span>
      </div>
    </div>
  </div>
</template>
