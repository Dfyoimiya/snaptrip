/**
 * Markdown 渲染 composable
 * 使用 marked 解析 + DOMPurify 消毒，安全输出 HTML
 */
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 配置 marked
marked.setOptions({
  breaks: true,        // 单换行 → <br>
  gfm: true,           // GitHub Flavored Markdown
})

// 自定义链接渲染：新窗口打开 + 安全属性
const renderer = new marked.Renderer()
renderer.link = ({ href, title, text }) => {
  const titleAttr = title ? ` title="${title}"` : ''
  const isInternal = href.startsWith('/')
  const targetAttr = isInternal ? '' : ' target="_blank" rel="noopener noreferrer"'
  return `<a href="${href}"${titleAttr}${targetAttr}>${text}</a>`
}

marked.use({ renderer })

export function renderMarkdown(raw: string): string {
  if (!raw) return ''
  const html = marked.parse(raw) as string
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'em', 'u', 's', 'del', 'code', 'pre',
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'ul', 'ol', 'li', 'blockquote',
      'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'hr', 'span', 'div',
    ],
    ALLOWED_ATTR: ['href', 'title', 'target', 'rel', 'src', 'alt', 'class'],
  })
}
