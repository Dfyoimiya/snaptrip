import type { ChatMessage } from "../../stores/chatStore"
import { PlanCard } from "./PlanCard"
import { MarkdownText } from "./MarkdownText"
import { Bot, User } from "lucide-react"

interface Props {
  message: ChatMessage
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user"

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div
        className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
          isUser
            ? "bg-stone-700 text-white"
            : "bg-emerald-100 text-emerald-700"
        }`}
      >
        {isUser ? <User size={14} /> : <Bot size={14} />}
      </div>

      {/* Content */}
      <div className={`flex-1 ${isUser ? "flex flex-col items-end" : ""}`}>
        {isUser ? (
          <div className="bg-stone-100 text-stone-800 text-sm rounded-2xl rounded-tr-md px-4 py-2.5 max-w-[85%]">
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
        ) : (
          <div className="text-sm text-stone-700 max-w-[90%]">
            {/* Text content with markdown rendering */}
            {message.content ? (
              <div className="prose-clean">
                <MarkdownText>{message.content}</MarkdownText>
              </div>
            ) : !message.plan ? (
              /* Loading skeleton — only when no content and no plan yet */
              <div className="space-y-2 py-1">
                <div className="h-3 bg-stone-200 rounded animate-pulse w-[85%]" />
                <div className="h-3 bg-stone-200 rounded animate-pulse w-[60%]" />
                <div className="h-3 bg-stone-200 rounded animate-pulse w-[40%]" />
              </div>
            ) : null}

            {/* Plan card */}
            {message.plan && (
              <div className="mt-3">
                <PlanCard plan={message.plan} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
