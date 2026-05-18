import { useRef, useState } from "react"
import { SendHorizontal } from "lucide-react"

interface Props {
  onSend: (text: string) => void
  disabled: boolean
}

export function InputBar({ onSend, disabled }: Props) {
  const [text, setText] = useState("")
  const ref = useRef<HTMLInputElement>(null)

  function handleSend() {
    const v = text.trim()
    if (!v || disabled) return
    onSend(v)
    setText("")
    ref.current?.focus()
  }

  return (
    <div className="flex items-center gap-3 px-4 py-3 border-t border-zinc-800 bg-zinc-900">
      <input
        ref={ref}
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSend()}
        placeholder="想去北京故宫逛逛..."
        disabled={disabled}
        className="flex-1 bg-zinc-800 text-sm text-zinc-100 placeholder-zinc-500 rounded-lg px-4 py-2.5 outline-none border border-zinc-700 focus:border-rose-500/50 transition-colors disabled:opacity-40"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="p-2.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <SendHorizontal size={16} />
      </button>
    </div>
  )
}
