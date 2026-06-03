import { useState } from "react"
import { Check, Loader2 } from "lucide-react"
import type { OptionItem } from "../../types/agent"

interface Props {
  option: OptionItem
  selected: boolean
  disabled: boolean
  loading: boolean
  onClick: () => void
}

export function OptionCard({ option, selected, disabled, loading, onClick }: Props) {
  const [hovered, setHovered] = useState(false)

  // Derive value from label if empty
  const value = option.value || option.label

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`
        w-full text-left px-4 py-3 rounded-xl border transition-all duration-200
        disabled:cursor-not-allowed group
        ${selected
          ? "border-emerald-400 bg-emerald-50/50 shadow-sm"
          : "border-stone-200 bg-white hover:border-stone-300 hover:shadow-sm hover:-translate-y-0.5"
        }
      `}
    >
      <div className="flex items-start gap-3">
        {/* Radio indicator */}
        <div
          className={`
            shrink-0 mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center
            transition-colors duration-200
            ${selected
              ? "border-emerald-500 bg-emerald-500"
              : "border-stone-300 group-hover:border-stone-400"
            }
          `}
        >
          {loading ? (
            <Loader2 size={12} className="animate-spin text-white" />
          ) : selected ? (
            <Check size={12} className="text-white" />
          ) : null}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`
                text-sm font-medium transition-colors
                ${selected ? "text-emerald-800" : "text-stone-700"}
              `}
            >
              {option.label}
            </span>
            {value !== option.label && (
              <span className="text-[10px] text-stone-400 font-mono bg-stone-100 px-1.5 py-0.5 rounded">
                {value}
              </span>
            )}
          </div>
          {option.description && (
            <p className="text-xs text-stone-400 mt-0.5 leading-relaxed">
              {option.description}
            </p>
          )}
        </div>

        {/* Hover glow */}
        {hovered && !selected && !disabled && (
          <div className="shrink-0 self-center w-1.5 h-1.5 rounded-full bg-stone-300 animate-pulse" />
        )}
      </div>
    </button>
  )
}
