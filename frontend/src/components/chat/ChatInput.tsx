import { useState, useRef, useEffect } from "react"
import { SendHorizontal } from "lucide-react"

interface Props {
  onSend: (text: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled, placeholder }: Props) {
  const [text, setText] = useState("")
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!disabled && inputRef.current) {
      inputRef.current.focus()
    }
  }, [disabled])

  function handleSubmit() {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText("")
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // Auto-resize textarea
  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value)
    const el = e.target
    el.style.height = "auto"
    el.style.height = Math.min(el.scrollHeight, 200) + "px"
  }

  return (
    <div className="border-t border-stone-200 bg-stone-50 px-4 py-3">
      <div className="max-w-2xl mx-auto flex items-end gap-2 bg-white border border-stone-200 rounded-xl px-4 py-2 shadow-sm focus-within:border-stone-300 focus-within:shadow-md transition-all">
        <textarea
          ref={inputRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder ?? "比如：周末带孩子去朝阳公园玩…"}
          rows={1}
          className="flex-1 bg-transparent text-sm text-stone-800 placeholder:text-stone-400 resize-none outline-none py-1.5 max-h-[200px]"
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || !text.trim()}
          className="shrink-0 p-1.5 rounded-lg text-stone-400 hover:text-stone-600 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <SendHorizontal size={18} />
        </button>
      </div>
      <p className="text-[10px] text-stone-400 text-center mt-2">
        SnapTrip 可能会产生不准确信息，请核实关键信息。
      </p>
    </div>
  )
}
