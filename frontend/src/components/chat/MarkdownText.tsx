import type { Components } from "react-markdown"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface Props {
  children: string
  /** If true, renders table/code-block-friendly styles */
  compact?: boolean
}

/**
 * Shared markdown renderer used across all chat components.
 *
 * Supports:
 * - GitHub Flavored Markdown (tables, task lists, strikethrough)
 * - Secure external links (target="_blank" rel="noopener")
 * - Tailwind-styled tables, code blocks, paragraphs
 */
export function MarkdownText({ children, compact = false }: Props) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={COMPONENTS(compact)}
    >
      {children}
    </ReactMarkdown>
  )
}

function COMPONENTS(compact: boolean): Partial<Components> {
  return {
    // Links: open in new tab
    a({ href, children, ...props }) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-emerald-600 underline hover:text-emerald-700"
          {...props}
        >
          {children}
        </a>
      )
    },

    // Paragraphs
    p({ children }) {
      return <p className={compact ? "my-1" : "my-1.5"}>{children}</p>
    },

    // Code blocks
    code({ className, children, ...props }) {
      const isInline = !className
      if (isInline) {
        return (
          <code
            className="bg-stone-100 text-stone-700 rounded px-1 py-0.5 text-[0.85em] font-mono"
            {...props}
          >
            {children}
          </code>
        )
      }
      return (
        <pre className="bg-stone-900 text-stone-100 rounded-lg p-3 overflow-x-auto my-2 text-xs">
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      )
    },

    // Tables
    table({ children }) {
      return (
        <div className="overflow-x-auto my-2">
          <table className="w-full text-xs border-collapse border border-stone-200 rounded-lg overflow-hidden">
            {children}
          </table>
        </div>
      )
    },
    thead({ children }) {
      return <thead className="bg-stone-50">{children}</thead>
    },
    th({ children }) {
      return (
        <th className="border border-stone-200 px-2 py-1.5 text-left font-medium text-stone-600">
          {children}
        </th>
      )
    },
    td({ children }) {
      return (
        <td className="border border-stone-200 px-2 py-1.5 text-stone-700">
          {children}
        </td>
      )
    },

    // Lists
    ul({ children }) {
      return <ul className="list-disc pl-5 my-1.5 space-y-0.5 text-sm">{children}</ul>
    },
    ol({ children }) {
      return <ol className="list-decimal pl-5 my-1.5 space-y-0.5 text-sm">{children}</ol>
    },

    // Emphasis
    strong({ children }) {
      return <strong className="font-semibold text-stone-800">{children}</strong>
    },
    em({ children }) {
      return <em className="italic text-stone-600">{children}</em>
    },

    // Headings
    h1({ children }) {
      return <h1 className="text-base font-semibold text-stone-800 mt-3 mb-1.5">{children}</h1>
    },
    h2({ children }) {
      return <h2 className="text-sm font-semibold text-stone-800 mt-2.5 mb-1">{children}</h2>
    },
    h3({ children }) {
      return <h3 className="text-sm font-medium text-stone-700 mt-2 mb-0.5">{children}</h3>
    },

    // Blockquote
    blockquote({ children }) {
      return (
        <blockquote className="border-l-3 border-stone-300 pl-3 text-stone-500 italic my-2 text-sm">
          {children}
        </blockquote>
      )
    },

    // Horizontal rule
    hr() {
      return <hr className="border-stone-200 my-3" />
    },
  }
}
