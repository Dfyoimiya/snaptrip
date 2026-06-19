export interface ProductImageRule {
  keywords: string[]
  imageUrl: string
}

const imageParams = '?auto=format&fit=crop&w=800&q=85'

export const productImageRules: ProductImageRule[] = [
  {
    keywords: ['iphone'],
    imageUrl: `https://images.unsplash.com/photo-1592750475338-74b7b21085ab${imageParams}`,
  },
  {
    keywords: ['macbook', '笔记本电脑', '电脑'],
    imageUrl: `https://images.unsplash.com/photo-1517336714731-489689fd1ca8${imageParams}`,
  },
  {
    keywords: ['galaxy', 'xiaomi', 'mate', '手机'],
    imageUrl: `https://images.unsplash.com/photo-1511707171634-5f897ff02aa9${imageParams}`,
  },
  {
    keywords: ['air jordan', 'ultraboost', '运动鞋', '跑步鞋'],
    imageUrl: `https://images.unsplash.com/photo-1542291026-7eec264c27ff${imageParams}`,
  },
  {
    keywords: ['sony', '耳机', '音箱'],
    imageUrl: `https://images.unsplash.com/photo-1505740420928-5e560c06d30e${imageParams}`,
  },
  {
    keywords: ['sk-ii', '护肤', '精华', '美容'],
    imageUrl: `https://images.unsplash.com/photo-1556228578-0d85b1a4d571${imageParams}`,
  },
  {
    keywords: ['戴森', '吹风机', '个护'],
    imageUrl: `https://images.unsplash.com/photo-1522338242992-e1a54906a8da${imageParams}`,
  },
]

export const defaultProductImage =
  `https://images.unsplash.com/photo-1472851294608-062f824d29cc${imageParams}`

export function resolveProductImage(productName: string, apiImage?: string | null): string {
  const normalizedName = productName.trim().toLowerCase()
  const matchedRule = productImageRules.find((rule) =>
    rule.keywords.some((keyword) => normalizedName.includes(keyword.toLowerCase())),
  )

  if (matchedRule) return matchedRule.imageUrl
  if (apiImage && !apiImage.includes('picsum.photos')) return apiImage
  return defaultProductImage
}
