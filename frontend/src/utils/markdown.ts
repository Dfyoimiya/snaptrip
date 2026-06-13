/** Markdown rendering utility — marked + DOMPurify for safe, rich AI responses. */

import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Configure marked for admin chat display
marked.setOptions({
  breaks: true,         // Single line breaks render as <br>
  gfm: true,            // GitHub Flavored Markdown (tables, task lists, strikethrough)
})

/**
 * Render raw markdown string to safe HTML.
 * Uses DOMPurify to prevent XSS — critical since content comes from LLM.
 */
export function renderMarkdown(raw: string): string {
  if (!raw) return ''
  const html = marked.parse(raw) as string
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'em', 'u', 's', 'del',
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'ul', 'ol', 'li',
      'a', 'img',
      'code', 'pre',
      'blockquote',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'hr',
      'span', 'div',
    ],
    ALLOWED_ATTR: [
      'href', 'target', 'rel', 'src', 'alt', 'class',
    ],
  })
}
