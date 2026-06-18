# SnapTrip Mall-Web 前端重构设计方案

> 版本：v1.0  
> 日期：2025-07-07  
> 主题：Apple Liquid Glass 液态玻璃设计语言 + 技术栈全面升级

---

## 一、重构愿景

将现有的 `mall-web`（Vue 3 + TailwindCSS）全面重构为 **React 19 + Next.js 15 + Liquid Glass 设计系统**。

新前端将以 **Apple Liquid Glass** 为核心视觉语言，打造通透、折射、流动的电商体验。用户滑动页面时，商品内容如悬浮于玻璃层之上；导航栏、卡片、模态框都带有真实的玻璃折射质感，光随动，影随变。

---

## 二、Apple Liquid Glass 设计语言深度解析

### 2.1 核心特征（WWDC 2025 官方定义）

| 特征           | 说明                                   | 前端实现方向                                              |
| -------------- | -------------------------------------- | --------------------------------------------------------- |
| **半透明折射** | 背景内容通过玻璃层动态折射，非静态模糊 | `backdrop-filter: blur()` + `saturate()` + `opacity` 组合 |
| **镜面高光**   | 玻璃表面有随光线变化的光泽反射         | 伪元素 `::before` + 线性渐变 + 角度动画                   |
| **流体形态**   | 控件可随交互变形、拉伸、光晕扩散       | Framer Motion `layout` + `whileHover` + `whileTap`        |
| **环境感知**   | 自动适配浅色/深色背景，颜色动态折射    | CSS 变量 + `color-mix()` + 系统主题监听                   |
| **层次景深**   | 多层玻璃叠加，每层折射率不同           | `z-index` 分层 + 不同 `blur` 强度 + 微妙阴影              |
| **实时响应**   | 滚动、点击、拖拽时实时反馈             | 滚动驱动动画 + 交互状态过渡                               |

### 2.2 与 Glassmorphism 的本质区别

```
Glassmorphism（2020）                    Liquid Glass（2025）
─────────────────────────────           ────────────────────────────
静态模糊背景                              动态折射 + 物理真实感
统一模糊半径                              根据内容密度自适应模糊
无高光                                    镜面高光 + 光泽反射
无动效                                    流体形态 + 光随动
简单半透明                                多层景深 + 环境感知
```

### 2.3 电商场景适配要点

- **商品卡片**：悬浮玻璃卡片，背景商品图通过玻璃层折射，增加 "悬浮陈列" 感
- **导航栏**：滚动后变为透明玻璃态，不占视觉空间
- **购物车/侧边栏**：侧边滑入的玻璃面板，内容在其后折射
- **价格/按钮**：玻璃质感按钮，hover 时光晕扩散
- **模态框/弹窗**：从点击位置展开的玻璃气泡，而非生硬矩形
- **搜索框**：聚焦时边框变为流光玻璃边缘

---

## 三、新架构技术栈（全面切换）

### 3.1 核心选型

| 层级         | 旧技术栈       | 新技术栈                  | 选型理由                                                     |
| ------------ | -------------- | ------------------------- | ------------------------------------------------------------ |
| **框架**     | Vue 3.5        | **React 19**              | 生态更丰富，Server Components 更成熟，Liquid Glass 社区资源以 React 为主 |
| **全栈框架** | Vite 8         | **Next.js 15**            | App Router、Server Components、PPR、自动优化、生态首选       |
| **渲染**     | SPA CSR        | **SSR + RSC + PPR**       | 首屏加载、SEO、商品详情页需要静态缓存                        |
| **语言**     | TypeScript 6   | **TypeScript 5.7+**       | 保持严格模式，React 19 类型定义更完善                        |
| **样式**     | Tailwind CSS 3 | **Tailwind CSS 4**        | CSS-first 配置，内置变量，更快的增量构建                     |
| **组件库**   | 手写原子类     | **shadcn/ui + Radix**     | 白盒组件，完全可定制，天然适配 Liquid Glass 改造             |
| **动画**     | 原生 CSS       | **Framer Motion**         | 声明式动画，layout 动画、共享元素过渡、手势交互              |
| **状态**     | Pinia 3        | **Zustand 5**             | 轻量、无 Provider 包裹、持久化中间件、TypeScript 友好        |
| **数据获取** | Axios 手写     | **TanStack Query 5**      | 服务器状态管理、缓存、乐观更新、配合 RSC 完美工作            |
| **表单**     | 手写           | **React Hook Form + Zod** | 类型安全表单验证、性能优异                                   |
| **字体**     | 系统字体       | **Inter + next/font**     | 优化加载、字体回退                                           |
| **图标**     | SVG 内联       | **Lucide React**          | 与 shadcn/ui 原生兼容、tree-shakeable                        |
| **构建**     | Vite           | **Turbopack**             | Next.js 15 默认、极快 HMR、内存优化                          |

### 3.2 依赖清单

```bash
# 核心框架
next@latest          # Next.js 15 (App Router)
react@latest         # React 19
react-dom@latest     # React DOM 19

# 样式
tailwindcss@4        # Tailwind CSS v4 (CSS-first)
@tailwindcss/postcss # PostCSS 集成
postcss@8            # CSS 处理

# 组件系统
shadcn/ui            # npx shadcn@latest init 初始化
radix-ui/*           # shadcn 底层依赖（按需）
class-variance-authority # CVA 组件变体
clsx                 # 条件类名
tailwind-merge       # 合并 Tailwind 类名

# 动画
framer-motion@latest # 动画引擎

# 状态管理
zustand@5            # 全局状态
zustand/middleware   # 持久化、日志

# 数据获取
tanstack/react-query@5  # 服务器状态管理
@tanstack/react-query-devtools # 开发工具

# 表单与验证
react-hook-form@7    # 表单管理
zod@3                # 类型安全验证
@hookform/resolvers  # 桥接 Zod

# 图标
lucide-react@latest  # 图标库

# 工具
next-themes@latest   # 主题切换（明暗/系统）
date-fns@latest      # 日期处理

# 开发依赖
typescript@5.7
@types/react
@types/react-dom
@types/node
vitest@3             # 测试
@testing-library/react # React 测试工具
playwright@latest    # E2E 测试
eslint@9
prettier@3
```

---

## 四、项目目录结构（App Router）

```
frontend-v2/                          # 新前端目录
├── app/                              # Next.js App Router
│   ├── (marketing)/                  # 营销页面组（无导航栏）
│   │   ├── landing/
│   │   │   └── page.tsx
│   │   └── layout.tsx
│   ├── (shop)/                       # 商城主页面组
│   │   ├── page.tsx                  # 首页 (HomeView)
│   │   ├── search/
│   │   │   └── page.tsx              # 搜索页
│   │   ├── category/
│   │   │   └── page.tsx              # 分类页
│   │   ├── product/
│   │   │   └── [id]/
│   │   │       └── page.tsx          # 商品详情 (SSG/ISR)
│   │   ├── brand/
│   │   │   └── [id]/
│   │   │       └── page.tsx          # 品牌详情
│   │   ├── cart/
│   │   │   └── page.tsx              # 购物车
│   │   ├── checkout/
│   │   │   └── page.tsx              # 结算
│   │   ├── order/
│   │   │   └── [id]/
│   │   │       └── page.tsx          # 订单详情
│   │   ├── member/
│   │   │   ├── layout.tsx            # 会员中心布局
│   │   │   ├── page.tsx              # 个人中心
│   │   │   ├── orders/
│   │   │   │   └── page.tsx
│   │   │   ├── favorites/
│   │   │   │   └── page.tsx
│   │   │   └── settings/
│   │   │       └── page.tsx
│   │   └── layout.tsx                # 商城主布局 (Glass Layout)
│   ├── api/                          # API 路由（代理后端）
│   │   ├── auth/
│   │   │   └── [...nextauth]/        # 若使用 NextAuth
│   │   └── proxy/
│   │       └── [...path]/
│   │           └── route.ts
│   ├── auth/
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── register/
│   │       └── page.tsx
│   ├── layout.tsx                    # 根布局
│   ├── globals.css                   # 全局样式 + Liquid Glass 基础
│   └── loading.tsx                   # 全局加载态
│
├── components/
│   ├── ui/                           # shadcn/ui 组件（基础层）
│   │   ├── button.tsx                # 玻璃按钮变体
│   │   ├── card.tsx                  # 玻璃卡片
│   │   ├── dialog.tsx                # 玻璃弹窗
│   │   ├── input.tsx                 # 玻璃输入框
│   │   ├── badge.tsx                 # 玻璃标签
│   │   ├── sheet.tsx                 # 玻璃侧边栏
│   │   ├── skeleton.tsx              # 玻璃骨架屏
│   │   ├── toast.tsx                 # 玻璃 Toast
│   │   ├── tooltip.tsx               # 玻璃提示
│   │   ├── dropdown-menu.tsx         # 玻璃下拉菜单
│   │   ├── tabs.tsx                  # 玻璃标签页
│   │   ├── carousel.tsx              # 轮播（玻璃外壳）
│   │   └── ...                       # 按需添加
│   ├── glass/                        # Liquid Glass 专属组件（核心层）
│   │   ├── GlassCard.tsx             # 玻璃卡片（带折射、高光）
│   │   ├── GlassPanel.tsx            # 玻璃面板（侧边栏、模态）
│   │   ├── GlassButton.tsx           # 玻璃按钮（hover 光晕）
│   │   ├── GlassNavigation.tsx       # 玻璃导航栏（滚动透明化）
│   │   ├── GlassInput.tsx            # 玻璃输入框（聚焦流光）
│   │   ├── GlassPrice.tsx            # 玻璃价格展示（毛玻璃背景）
│   │   ├── GlassBadge.tsx            # 玻璃标签（新品/优惠）
│   │   ├── GlassAvatar.tsx           # 玻璃头像/品牌图标
│   │   ├── GlassModal.tsx            # 玻璃模态框（从点击位置展开）
│   │   ├── GlassTooltip.tsx          # 玻璃气泡提示
│   │   ├── GlassCountdown.tsx        # 玻璃倒计时（秒杀）
│   │   ├── GlassDivider.tsx          # 玻璃分隔线（半透明）
│   │   ├── GlassBackground.tsx       # 玻璃背景容器（全局）
│   │   ├── GlassReflection.tsx       # 镜面高光层（伪元素封装）
│   │   ├── GlassSheen.tsx            # 玻璃光泽动画（光扫过）
│   │   └── GlassLayer.tsx            # 玻璃层级系统（z-index + blur）
│   ├── product/                      # 商品业务组件
│   │   ├── ProductCard.tsx           # 商品卡片（玻璃态）
│   │   ├── ProductGrid.tsx           # 商品网格
│   │   ├── ProductImage.tsx          # 商品图片（带玻璃 overlay）
│   │   ├── ProductPrice.tsx          # 价格组件
│   │   ├── ProductTag.tsx            # 商品标签（限时/新品/优惠）
│   │   ├── ProductSkeleton.tsx       # 商品骨架屏
│   │   ├── ProductCarousel.tsx       # 商品轮播
│   │   └── ProductDetail.tsx         # 商品详情（复杂组合）
│   ├── layout/                       # 布局组件
│   │   ├── GlassHeader.tsx           # 玻璃头部（导航+搜索+购物车）
│   │   ├── GlassFooter.tsx           # 玻璃页脚
│   │   ├── GlassSidebar.tsx          # 玻璃侧边栏（分类导航）
│   │   ├── GlassSearchBar.tsx        # 玻璃搜索栏
│   │   ├── GlassCartTrigger.tsx      # 玻璃购物车触发器
│   │   ├── GlassBreadcrumb.tsx       # 面包屑导航
│   │   └── GlassLayout.tsx           # 玻璃主布局组合
│   ├── home/                         # 首页专属组件
│   │   ├── HeroSection.tsx           # 首屏（分类+轮播）
│   │   ├── CategoryNav.tsx           # 分类导航
│   │   ├── BannerCarousel.tsx        # 轮播图（玻璃外壳）
│   │   ├── SeckillSection.tsx        # 秒杀专区
│   │   ├── BrandSection.tsx          # 品牌推荐
│   │   ├── FeedSection.tsx           # 多维度推荐 Feed
│   │   └── HomeRecommend.tsx         # 为你推荐
│   ├── cart/                         # 购物车组件
│   ├── checkout/                     # 结算组件
│   ├── chat/                         # AI 客服组件（玻璃态）
│   └── shopping-guide/               # 导购组件
│
├── hooks/                            # 自定义 Hooks
│   ├── useGlassTheme.ts              # 玻璃主题感知（明暗/色彩）
│   ├── useGlassScroll.ts             # 滚动驱动玻璃变化（导航栏透明）
│   ├── useGlassRefraction.ts         # 折射效果计算（根据背景色）
│   ├── useCarousel.ts                # 轮播逻辑
│   ├── useCountdown.ts               # 倒计时逻辑
│   ├── useDebounce.ts                # 防抖
│   ├── useMediaQuery.ts              # 响应式
│   └── useCart.ts                    # 购物车操作
│
├── lib/                              # 工具库
│   ├── utils.ts                      # 通用工具（cn 函数等）
│   ├── glass-utils.ts                # 玻璃效果工具（颜色计算、blur 值）
│   ├── api.ts                        # API 封装（基于 fetch）
│   ├── fetcher.ts                    # TanStack Query 数据获取器
│   ├── auth.ts                       # 认证工具
│   ├── constants.ts                  # 常量
│   └── storage.ts                    # 存储封装（localStorage 抽象）
│
├── stores/                           # Zustand 状态管理
│   ├── useAuthStore.ts               # 认证状态（token + 用户信息）
│   ├── useCartStore.ts               # 购物车状态
│   ├── useUIStore.ts                 # UI 状态（侧边栏、弹窗、主题）
│   ├── useChatStore.ts               # 客服状态
│   └── useSearchStore.ts             # 搜索状态
│
├── types/                            # 类型定义（严格分层）
│   ├── api/                          # API 请求/响应类型
│   │   ├── home.ts
│   │   ├── product.ts
│   │   ├── cart.ts
│   │   ├── order.ts
│   │   ├── member.ts
│   │   ├── auth.ts
│   │   └── common.ts                 # CommonResult, CommonPage
│   ├── models/                       # 后端模型映射（前端统一命名）
│   │   ├── product.ts                # ProductModel（统一 camelCase）
│   │   ├── brand.ts
│   │   ├── category.ts
│   │   ├── member.ts
│   │   └── order.ts
│   ├── glass/                        # 玻璃设计系统类型
│   │   ├── tokens.ts                 # Design Token 类型
│   │   └── variants.ts               # 玻璃变体类型
│   └── index.ts                      # 统一导出
│
├── styles/                           # 全局样式
│   ├── globals.css                   # Tailwind 导入 + CSS 变量
│   ├── glass-tokens.css              # Liquid Glass 设计令牌
│   ├── glass-animations.css          # 玻璃动画关键帧
│   └── glass-shine.css               # 光泽/高光效果
│
├── public/                           # 静态资源
│   ├── images/
│   ├── fonts/
│   └── icons/
│
├── next.config.ts                    # Next.js 配置
├── tailwind.config.ts                # Tailwind 配置（自定义 glass 工具）
├── tsconfig.json                     # TypeScript 配置
├── postcss.config.mjs                # PostCSS 配置
├── package.json                      # 依赖
├── vitest.config.ts                  # 测试配置
├── playwright.config.ts              # E2E 测试配置
├── .env.local                        # 环境变量
├── .env.example                      # 环境变量示例
└── README.md                         # 项目说明
```

---

## 五、Liquid Glass 设计系统（Design Token）

### 5.1 CSS 变量定义（`styles/glass-tokens.css`）

```css
@layer base {
  :root {
    /* ── 玻璃基础材质 ── */
    --glass-bg: rgba(255, 255, 255, 0.08);
    --glass-bg-hover: rgba(255, 255, 255, 0.15);
    --glass-bg-active: rgba(255, 255, 255, 0.22);
    --glass-border: rgba(255, 255, 255, 0.18);
    --glass-border-light: rgba(255, 255, 255, 0.35);
    --glass-shadow: rgba(0, 0, 0, 0.12);
    --glass-shadow-lg: rgba(0, 0, 0, 0.25);
    
    /* ── 折射模糊强度 ── */
    --glass-blur-sm: 8px;
    --glass-blur-md: 16px;
    --glass-blur-lg: 24px;
    --glass-blur-xl: 40px;
    --glass-saturate: 180%;
    
    /* ── 高光反射 ── */
    --glass-sheen-opacity: 0.4;
    --glass-sheen-gradient: linear-gradient(
      135deg,
      rgba(255, 255, 255, 0.6) 0%,
      rgba(255, 255, 255, 0.1) 40%,
      rgba(255, 255, 255, 0) 50%,
      rgba(255, 255, 255, 0.1) 60%,
      rgba(255, 255, 255, 0.5) 100%
    );
    
    /* ── 颜色折射（品牌色渗透）── */
    --glass-tint-red: rgba(239, 68, 68, 0.08);
    --glass-tint-blue: rgba(59, 130, 246, 0.08);
    --glass-tint-purple: rgba(147, 51, 234, 0.08);
    
    /* ── 间距系统（与 Tailwind 对齐）── */
    --glass-radius-sm: 12px;
    --glass-radius-md: 20px;
    --glass-radius-lg: 28px;
    --glass-radius-xl: 40px;
    --glass-radius-full: 9999px;
    
    /* ── 动画速度 ── */
    --glass-transition-fast: 150ms;
    --glass-transition-base: 250ms;
    --glass-transition-slow: 400ms;
    --glass-easing: cubic-bezier(0.22, 1, 0.36, 1);
  }
  
  .dark {
    /* 深色模式：玻璃更暗，高光更亮 */
    --glass-bg: rgba(0, 0, 0, 0.25);
    --glass-bg-hover: rgba(0, 0, 0, 0.35);
    --glass-bg-active: rgba(0, 0, 0, 0.45);
    --glass-border: rgba(255, 255, 255, 0.12);
    --glass-border-light: rgba(255, 255, 255, 0.25);
    --glass-shadow: rgba(0, 0, 0, 0.35);
    --glass-sheen-opacity: 0.25;
  }
}
```

### 5.2 Tailwind CSS 4 自定义工具（`tailwind.config.ts`）

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        glass: {
          bg: "var(--glass-bg)",
          "bg-hover": "var(--glass-bg-hover)",
          "bg-active": "var(--glass-bg-active)",
          border: "var(--glass-border)",
          "border-light": "var(--glass-border-light)",
          shadow: "var(--glass-shadow)",
          "shadow-lg": "var(--glass-shadow-lg)",
        },
      },
      backdropBlur: {
        glass: "var(--glass-blur-md)",
        "glass-sm": "var(--glass-blur-sm)",
        "glass-lg": "var(--glass-blur-lg)",
        "glass-xl": "var(--glass-blur-xl)",
      },
      borderRadius: {
        "glass-sm": "var(--glass-radius-sm)",
        "glass-md": "var(--glass-radius-md)",
        "glass-lg": "var(--glass-radius-lg)",
        "glass-xl": "var(--glass-radius-xl)",
      },
      transitionTimingFunction: {
        glass: "var(--glass-easing)",
      },
      transitionDuration: {
        "glass-fast": "var(--glass-transition-fast)",
        "glass-base": "var(--glass-transition-base)",
        "glass-slow": "var(--glass-transition-slow)",
      },
      animation: {
        "glass-sheen": "glass-sheen 3s ease-in-out infinite",
        "glass-pulse": "glass-pulse 2s ease-in-out infinite",
      },
      keyframes: {
        "glass-sheen": {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
        "glass-pulse": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
    },
  },
};
export default config;
```

---

## 六、Liquid Glass 核心组件设计

### 6.1 GlassCard（商品卡片）

```tsx
// components/glass/GlassCard.tsx
"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  blur?: "sm" | "md" | "lg" | "xl";
  tint?: "none" | "red" | "blue" | "purple";
  sheen?: boolean;
  hover?: "lift" | "glow" | "scale";
}

export function GlassCard({
  children,
  className,
  blur = "md",
  tint = "none",
  sheen = true,
  hover = "lift",
}: GlassCardProps) {
  const blurMap = {
    sm: "backdrop-blur-[8px]",
    md: "backdrop-blur-[16px]",
    lg: "backdrop-blur-[24px]",
    xl: "backdrop-blur-[40px]",
  };

  const tintMap = {
    none: "",
    red: "bg-red-500/5",
    blue: "bg-blue-500/5",
    purple: "bg-purple-500/5",
  };

  const hoverMap = {
    lift: "hover:-translate-y-1 hover:shadow-lg",
    glow: "hover:shadow-[0_0_30px_rgba(255,255,255,0.15)]",
    scale: "hover:scale-[1.02]",
  };

  return (
    <motion.div
      className={cn(
        "relative overflow-hidden rounded-[20px] border border-white/20",
        "bg-white/10 dark:bg-black/20",
        "transition-all duration-300 ease-glass",
        blurMap[blur],
        tintMap[tint],
        hoverMap[hover],
        className
      )}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: hover === "scale" ? 1.02 : 1 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* 镜面高光层 */}
      {sheen && (
        <div
          className="absolute inset-0 pointer-events-none opacity-0 hover:opacity-100 transition-opacity duration-500"
          style={{
            background: `linear-gradient(
              135deg,
              rgba(255,255,255,0.4) 0%,
              rgba(255,255,255,0.1) 45%,
              rgba(255,255,255,0) 50%,
              rgba(255,255,255,0.1) 55%,
              rgba(255,255,255,0.3) 100%
            )`,
          }}
        />
      )}
      
      {/* 折射边缘 */}
      <div className="absolute inset-0 rounded-[20px] pointer-events-none border border-white/10" />
      
      {children}
    </motion.div>
  );
}
```

### 6.2 GlassButton（玻璃按钮）

```tsx
// components/glass/GlassButton.tsx
"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface GlassButtonProps {
  children: React.ReactNode;
  className?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  onClick?: () => void;
  disabled?: boolean;
}

export function GlassButton({
  children,
  className,
  variant = "primary",
  size = "md",
  onClick,
  disabled,
}: GlassButtonProps) {
  const variantMap = {
    primary: "bg-white/15 hover:bg-white/25 border-white/30 text-white",
    secondary: "bg-white/5 hover:bg-white/10 border-white/20 text-white/90",
    ghost: "bg-transparent hover:bg-white/10 border-transparent text-white/80",
    danger: "bg-red-500/15 hover:bg-red-500/25 border-red-500/30 text-red-200",
  };

  const sizeMap = {
    sm: "px-4 py-2 text-sm",
    md: "px-6 py-3 text-base",
    lg: "px-8 py-4 text-lg",
  };

  return (
    <motion.button
      className={cn(
        "relative overflow-hidden rounded-full backdrop-blur-md",
        "border transition-all duration-250 ease-glass",
        "flex items-center justify-center gap-2",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        variantMap[variant],
        sizeMap[size],
        className
      )}
      onClick={onClick}
      disabled={disabled}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      whileFocus={{ 
        boxShadow: "0 0 0 3px rgba(255,255,255,0.3)" 
      }}
    >
      {/* 光晕效果 */}
      <motion.div
        className="absolute inset-0 rounded-full opacity-0"
        style={{
          background: "radial-gradient(circle at center, rgba(255,255,255,0.3) 0%, transparent 70%)",
        }}
        whileHover={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      />
      <span className="relative z-10">{children}</span>
    </motion.button>
  );
}
```

### 6.3 GlassNavigation（滚动透明化导航）

```tsx
// components/layout/GlassHeader.tsx
"use client";

import { useState, useEffect } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { cn } from "@/lib/utils";

export function GlassHeader() {
  const { scrollY } = useScroll();
  const [isScrolled, setIsScrolled] = useState(false);
  
  // 滚动超过 50px 后，导航栏变为玻璃态
  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // 背景透明度从 0 到 1
  const bgOpacity = useTransform(scrollY, [0, 100], [0, 1]);
  const blurStrength = useTransform(scrollY, [0, 100], [0, 16]);

  return (
    <motion.header
      className={cn(
        "fixed top-0 left-0 right-0 z-50",
        "border-b border-white/10"
      )}
      style={{
        backgroundColor: useTransform(bgOpacity, (v) => `rgba(0,0,0,${v * 0.7})`),
        backdropFilter: useTransform(blurStrength, (v) => `blur(${v}px)`),
      }}
    >
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <motion.div
          className="text-2xl font-bold text-white/90"
          whileHover={{ scale: 1.05 }}
        >
          SnapTrip
        </motion.div>
        
        {/* 导航链接 */}
        <nav className="hidden md:flex items-center gap-6">
          {["首页", "分类", "品牌", "新品"].map((item) => (
            <motion.a
              key={item}
              href="#"
              className="text-white/70 hover:text-white transition-colors"
              whileHover={{ y: -2 }}
            >
              {item}
            </motion.a>
          ))}
        </nav>
        
        {/* 搜索 + 购物车 */}
        <div className="flex items-center gap-4">
          <GlassSearchBar />
          <GlassCartTrigger />
        </div>
      </div>
    </motion.header>
  );
}
```

---

## 七、数据层与状态管理

### 7.1 API 封装（`lib/api.ts`）

```typescript
// 统一 API 层，基于 fetch，配合 TanStack Query
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

export async function fetcher<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: {
      "Content-Type": "application/json",
      "source-client": "pc",
    },
    ...options,
  });
  
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  
  const data = await res.json();
  // 后端 code=0 为成功
  if (data.code !== 0) throw new Error(data.message || "Request failed");
  
  // 统一转换为 camelCase（此处可用库如 humps）
  return data.data;
}

// 商品相关 API
export const getProduct = (id: string) => 
  fetcher<ProductModel>(`/api/v1/portal/products/${id}`);

export const searchProducts = (params: SearchParams) =>
  fetcher<PageResult<ProductModel>>(`/api/v1/portal/products?${qs(params)}`);

export const getHomeContent = () =>
  fetcher<HomeContent>(`/api/v1/portal/home`);
```

### 7.2 TanStack Query 集成（Server + Client）

```tsx
// app/layout.tsx (Server Component)
import { QueryClient, dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";

export default async function RootLayout({ children }) {
  const queryClient = getQueryClient();
  
  // 预取首页数据（可选）
  await queryClient.prefetchQuery({
    queryKey: ["home"],
    queryFn: getHomeContent,
  });
  
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      {children}
    </HydrationBoundary>
  );
}
```

```tsx
// 客户端组件使用
"use client";
import { useQuery } from "@tanstack/react-query";

export function ProductList() {
  const { data, isLoading } = useQuery({
    queryKey: ["products"],
    queryFn: () => searchProducts({ page: 1 }),
    staleTime: 60 * 1000, // 1 分钟
  });
  
  if (isLoading) return <ProductSkeletonGrid />;
  return (
    <div className="grid grid-cols-5 gap-4">
      {data?.items.map((product) => (
        <GlassCard key={product.id}>
          <ProductCardContent product={product} />
        </GlassCard>
      ))}
    </div>
  );
}
```

### 7.3 Zustand Store 设计（`stores/useCartStore.ts`）

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

interface CartItem {
  id: string;
  productId: string;
  name: string;
  price: number;
  quantity: number;
  image: string;
}

interface CartState {
  items: CartItem[];
  isOpen: boolean;
  // Actions
  addItem: (item: CartItem) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, qty: number) => void;
  toggleCart: () => void;
  totalCount: () => number;
  totalPrice: () => number;
}

export const useCartStore = create<CartState>()(
  persist(
    immer((set, get) => ({
      items: [],
      isOpen: false,
      
      addItem: (item) =>
        set((state) => {
          const existing = state.items.find((i) => i.productId === item.productId);
          if (existing) {
            existing.quantity += item.quantity;
          } else {
            state.items.push(item);
          }
        }),
      
      removeItem: (id) =>
        set((state) => {
          state.items = state.items.filter((i) => i.id !== id);
        }),
      
      updateQuantity: (id, qty) =>
        set((state) => {
          const item = state.items.find((i) => i.id === id);
          if (item) item.quantity = Math.max(1, qty);
        }),
      
      toggleCart: () =>
        set((state) => {
          state.isOpen = !state.isOpen;
        }),
      
      totalCount: () => get().items.reduce((s, i) => s + i.quantity, 0),
      totalPrice: () => get().items.reduce((s, i) => s + i.price * i.quantity, 0),
    })),
    { name: "snaptrip-cart" }
  )
);
```

---

## 八、页面重构对照表

| 旧页面（Vue）           | 新页面（Next.js App Router）       | 渲染策略  | 说明                       |
| ----------------------- | ---------------------------------- | --------- | -------------------------- |
| `HomeView.vue`          | `app/(shop)/page.tsx`              | PPR       | 静态 shell + 动态推荐流    |
| `ProductDetailView.vue` | `app/(shop)/product/[id]/page.tsx` | SSG + ISR | 商品详情静态化，定时重验证 |
| `SearchView.vue`        | `app/(shop)/search/page.tsx`       | SSR       | 搜索参数动态               |
| `CategoryView.vue`      | `app/(shop)/category/page.tsx`     | SSG       | 分类树静态化               |
| `CartView.vue`          | `app/(shop)/cart/page.tsx`         | CSR       | 强交互，客户端渲染         |
| `OrderConfirmView.vue`  | `app/(shop)/checkout/page.tsx`     | CSR       | 结算流程                   |
| `LoginView.vue`         | `app/auth/login/page.tsx`          | SSR       | 登录页                     |
| `MemberLayout.vue`      | `app/(shop)/member/layout.tsx`     | SSR       | 会员中心布局               |

---

## 九、性能优化策略

### 9.1 渲染策略矩阵

```
页面类型            策略              缓存策略
─────────────────────────────────────────────────────
首页                PPR               Static Shell + 
                                      Streaming Dynamic Parts
商品列表            SSR               1 分钟 stale-while-revalidate
商品详情            SSG + ISR         1 小时 ISR + On-demand Revalidation
购物车/结算         CSR               无（纯客户端）
会员中心            SSR               Session-based
```

### 9.2 关键优化点

- **图片优化**：`next/image` 自动 WebP/AVIF 转换、响应式尺寸、懒加载
- **字体优化**：`next/font` 自动子集化、CSS 变量注入
- **代码分割**：路由级自动分割 + 动态导入 heavy 组件（如 ChatWidget）
- **玻璃效果性能**：`backdrop-filter` 仅在 GPU 层使用，避免大面积模糊区域；提供 `prefers-reduced-motion` 降级
- **数据缓存**：TanStack Query 缓存 + Next.js Data Cache 双层缓存

### 9.3 Liquid Glass 性能降级方案

```css
/* 高性能模式（弱网/低设备） */
@media (prefers-reduced-motion: reduce) {
  .glass-effect {
    backdrop-filter: none !important;
    background: rgba(255,255,255,0.9) !important;
  }
}

/* 低功耗模式 */
.glass-effect-low-power {
  backdrop-filter: blur(8px) !important;
  /* 移除高光动画、折射计算 */
}
```

---

## 十、实施路线图

### Phase 1: 基础设施（1 周）

- [ ] 创建 `frontend-v2` 目录，初始化 Next.js 15 + Tailwind CSS 4
- [ ] 配置 TypeScript 严格模式、ESLint、Prettier
- [ ] 安装 shadcn/ui 并初始化（`npx shadcn@latest init`）
- [ ] 配置 `next-themes` 明暗模式切换
- [ ] 搭建基础布局（根 layout + 404/loading/error 边界）
- [ ] 配置 TanStack Query Provider + Zustand Provider
- [ ] 编写 API 封装层（对接后端现有接口）
- [ ] 类型定义迁移（从旧项目 `types/` 重新整理为 `types/models/` + `types/api/`）

### Phase 2: Liquid Glass 设计系统（1.5 周）

- [ ] 编写 `glass-tokens.css` 设计令牌
- [ ] 扩展 Tailwind 配置（glass 工具类）
- [ ] 实现核心玻璃组件：`GlassCard`, `GlassButton`, `GlassPanel`, `GlassInput`
- [ ] 实现 `GlassNavigation`（滚动透明化）
- [ ] 实现 `GlassReflection` 和 `GlassSheen` 效果层
- [ ] 编写玻璃动画 CSS（`glass-animations.css`）
- [ ] 组件 Storybook（可选）或本地文档

### Phase 3: 商品/首页页面重构（2 周）

- [ ] 商品卡片 `ProductCard`（GlassCard 包装）
- [ ] 商品网格 `ProductGrid` + 瀑布流/响应式
- [ ] 轮播组件 `BannerCarousel`（玻璃外壳）
- [ ] 分类导航 `CategoryNav`（玻璃侧边栏）
- [ ] 首页布局重组（Hero + Feed + 推荐）
- [ ] 数据接入（TanStack Query + Server Components）
- [ ] 加载态/错误态（GlassSkeleton, Error Boundary）

### Phase 4: 购物车/结算/会员中心（1.5 周）

- [ ] 购物车状态（Zustand + persist）
- [ ] 购物车页面（玻璃侧边栏滑出 + 全页）
- [ ] 结算流程（表单验证 + 步骤条）
- [ ] 会员中心布局 + 嵌套路由
- [ ] 订单列表/详情

### Phase 5: 认证/客服/打磨（1 周）

- [ ] 登录/注册页（玻璃表单）
- [ ] 认证中间件（路由保护）
- [ ] AI 客服组件（Glass 气泡）
- [ ] 全局 Toast 通知（玻璃态）
- [ ] 无障碍检查（键盘导航、屏幕阅读器、高对比度）
- [ ] 性能优化（Lighthouse 90+）

### Phase 6: 测试/部署（1 周）

- [ ] 单元测试（Vitest + React Testing Library）
- [ ] E2E 测试（Playwright：首页→搜索→商品→购物车→结算）
- [ ] 视觉回归测试（可选）
- [ ] 构建优化分析（Bundle Analyzer）
- [ ] Docker 容器化 + Nginx 部署配置
- [ ] 与后端联调（保持现有 API 契约）

**总计：8 周**（可压缩至 6 周，增加人力）

---

## 十一、风险与应对

| 风险                       | 影响 | 应对策略                                               |
| -------------------------- | ---- | ------------------------------------------------------ |
| `backdrop-filter` 性能问题 | 中   | 提供降级 CSS、检测设备性能动态切换                     |
| 旧 API 接口契约不一致      | 高   | Phase 1 即完成 API 层，统一字段映射                    |
| 深色模式文字可读性         | 中   | 严格对比度检查（WCAG 4.5:1）、Glass 文字带阴影/背景    |
| Next.js 15 学习成本        | 中   | 小团队逐步迁移，Server/Client 组件边界明确             |
| 玻璃效果浏览器兼容性       | 低   | 渐进增强，Firefox/Safari/Chrome 均已支持               |
| 原有数据丢失               | 高   | 购物车/用户数据存储格式兼容，localStorage key 保持不变 |

---

## 十二、总结

本次重构将 mall-web 从 **Vue 3 传统 SPA** 升级为 **Next.js 15 现代全栈应用**，核心亮点：

1. **Liquid Glass 设计语言**：通透、折射、流动的视觉体验，将电商界面从 "平面陈列" 升级为 "玻璃橱窗" 质感
2. **Server Components 架构**：首屏 SSR + 动态流式渲染，兼顾 SEO 与性能
3. **白盒组件系统**：shadcn/ui + 自定义 Glass 组件，完全可控、无黑盒
4. **现代化数据层**：TanStack Query 缓存 + Zustand 轻量状态，告别 Pinia 样板代码
5. **类型安全**：Zod 验证 + TypeScript 严格模式，消除 `as unknown as` 等类型 hack

> **下一步**：从 **Phase 1 基础设施** 开始执行，先初始化 Next.js 项目并验证 Liquid Glass 核心效果，确认后再展开全面页面重构。

---

*文档版本：v1.0 | 基于 Apple Liquid Glass WWDC 2025 设计规范 + React 19/Next.js 15 最佳实践*