import type { ReactNode } from 'react'
import {
  CheckCircle2,
  Loader2,
  MapPin,
  Sparkles,
  Workflow,
} from 'lucide-react'

function ConnectorH() {
  return (
    <div
      className="hidden shrink-0 md:block md:w-10 lg:w-14"
      aria-hidden
    >
      <div className="relative top-1/2 h-px -translate-y-1/2 bg-zinc-600/45" />
    </div>
  )
}

function ConnectorV() {
  return (
    <div className="flex justify-center py-2" aria-hidden>
      <div className="h-6 w-px bg-zinc-600/45" />
    </div>
  )
}

function PipelineNode({
  title,
  subtitle,
  status,
  children,
  className = '',
}: {
  title: string
  subtitle?: string
  status?: 'done' | 'active' | 'idle'
  children?: ReactNode
  className?: string
}) {
  const ring =
    status === 'active'
      ? 'ring-1 ring-cyan-500/35 shadow-[0_0_24px_rgba(34,211,238,0.08)]'
      : status === 'done'
        ? 'ring-1 ring-emerald-500/20'
        : 'ring-1 ring-white/[0.06]'

  return (
    <div
      className={`rounded-xl border border-white/10 bg-[#161616] px-4 py-3 ${ring} ${className}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">
            {title}
          </p>
          {subtitle ? (
            <p className="mt-1 text-sm font-medium tracking-tight text-zinc-200">
              {subtitle}
            </p>
          ) : null}
        </div>
        {status === 'done' ? (
          <CheckCircle2
            className="size-4 shrink-0 text-emerald-400/90"
            strokeWidth={1.5}
          />
        ) : null}
        {status === 'active' ? (
          <Loader2
            className="size-4 shrink-0 animate-spin text-cyan-400/90"
            strokeWidth={1.5}
          />
        ) : null}
      </div>
      {children}
    </div>
  )
}

function SubtaskCard({
  label,
  state,
}: {
  label: string
  state: 'done' | 'running'
}) {
  const isRun = state === 'running'
  return (
    <div
      className={`rounded-lg border border-white/10 bg-black/40 px-3 py-2.5 ${
        isRun
          ? 'shadow-[0_0_0_1px_rgba(251,191,36,0.15)_inset] animate-pulse'
          : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[12px] leading-snug text-zinc-300">{label}</span>
        <span className="shrink-0 text-[11px] font-medium tabular-nums">
          {state === 'done' ? (
            <span className="text-emerald-400/95">🟢 已完成</span>
          ) : (
            <span className="text-amber-300/95">🟡 运行中</span>
          )}
        </span>
      </div>
    </div>
  )
}

function AgentExecutionPanel() {
  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col rounded-2xl border border-white/10 bg-[#141414] shadow-[0_0_0_1px_rgba(255,255,255,0.02)_inset]">
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-white/10 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg border border-white/10 bg-black/50">
            <Workflow className="size-4 text-zinc-400" strokeWidth={1.5} />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-zinc-100">
              Agent Execution Pipeline
            </h1>
            <p className="text-[12px] text-zinc-500">
              多任务并行 · DAG 调度 · 实时观测
            </p>
          </div>
        </div>
        <div className="hidden items-center gap-2 sm:flex">
          <span className="rounded-md border border-emerald-500/25 bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
            Live
          </span>
          <span className="rounded-md border border-white/10 bg-black/30 px-2 py-1 font-mono text-[10px] text-zinc-500">
            shard 02
          </span>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-auto px-4 py-8 sm:px-8">
        {/* Primary DAG row */}
        <div className="flex flex-col gap-6 lg:flex-row lg:items-stretch">
          <PipelineNode
            title="Stage 01"
            subtitle="意图解析"
            status="done"
            className="lg:max-w-[220px] lg:flex-1"
          >
            <p className="mt-3 font-mono text-[11px] leading-relaxed text-zinc-500">
              slots · tonight · party=2{'\n'}
              prefs · low_noise · movie_after_dinner
            </p>
          </PipelineNode>

          <div className="flex items-center gap-0 lg:flex-col lg:justify-center">
            <ConnectorH />
            <div className="h-8 w-px bg-zinc-600/45 lg:hidden" />
          </div>

          <PipelineNode
            title="Stage 02"
            subtitle="并行检索 POI"
            status="done"
            className="lg:max-w-[260px] lg:flex-1"
          >
            <p className="mt-3 font-mono text-[11px] text-zinc-500">
              POI fan-out · 50 candidates · dedupe · rank
            </p>
          </PipelineNode>

          <div className="flex items-center gap-0 lg:flex-col lg:justify-center">
            <ConnectorH />
            <div className="h-8 w-px bg-zinc-600/45 lg:hidden" />
          </div>

          <div className="min-w-0 flex-1 lg:min-w-[320px]">
            <PipelineNode
              title="Stage 03"
              subtitle="执行预订"
              status="active"
              className="h-full"
            >
              <ConnectorV />
              <div className="grid gap-2 sm:grid-cols-3">
                <SubtaskCard label="查询排队时长" state="done" />
                <SubtaskCard label="锁定餐位" state="running" />
                <SubtaskCard label="购买电影票" state="running" />
              </div>
              <p className="mt-3 font-mono text-[10px] leading-relaxed text-zinc-600">
                parallel_workers=3 · mutex=seat_hold · timeout=18s
              </p>
            </PipelineNode>
          </div>
        </div>

        {/* Decorative faint guides */}
        <div className="pointer-events-none mt-10 hidden border-t border-dashed border-white/[0.06] pt-6 lg:block">
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-zinc-700">
            trace · evt_booking_0193 · causal_depth=3
          </p>
        </div>
      </div>
    </section>
  )
}

function MiniMapPlaceholder() {
  return (
    <div className="relative h-[240px] shrink-0 overflow-hidden rounded-xl border border-white/10 bg-[#0c0c0c]">
      <div
        className="absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)
          `,
          backgroundSize: '20px 20px',
        }}
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,rgba(255,255,255,0.06),transparent_55%)]" />
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="flex size-12 items-center justify-center rounded-full border border-white/15 bg-black/60 shadow-[0_0_24px_rgba(0,0,0,0.65)] backdrop-blur-sm">
          <MapPin className="size-5 text-zinc-300" strokeWidth={1.5} />
        </div>
      </div>
      <div className="absolute bottom-3 left-3 font-mono text-[10px] uppercase tracking-wider text-zinc-600">
        Spatial · preview
      </div>
    </div>
  )
}

function TimelineSidebar() {
  return (
    <aside className="flex min-h-0 w-full min-w-0 flex-col gap-5 border-white/10 lg:border-l lg:pl-6">
      <MiniMapPlaceholder />

      <div className="min-h-0 flex-1 space-y-3 overflow-auto pb-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-zinc-500">
          Itinerary Timeline
        </p>

        <article className="rounded-xl border border-white/10 bg-[#141414] px-4 py-3">
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-mono text-[13px] font-medium tabular-nums text-zinc-200">
              19:00
            </span>
            <span className="text-[10px] uppercase tracking-wider text-zinc-600">
              Confirmed
            </span>
          </div>
          <p className="mt-1.5 text-[13px] font-medium leading-snug text-zinc-100">
            Bistro 108 餐酒馆
          </p>
          <p className="mt-2 font-mono text-[11px] text-zinc-500">
            预订确认码:{' '}
            <span className="text-zinc-300">8X92M</span>
          </p>
        </article>

        <article className="rounded-xl border border-white/10 bg-[#141414] px-4 py-3">
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-mono text-[13px] font-medium tabular-nums text-zinc-200">
              21:30
            </span>
            <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-amber-400/90">
              <span
                className="size-1.5 rounded-full bg-amber-400"
                style={{ animation: 'node-pulse 1.4s ease-in-out infinite' }}
              />
              Issuing
            </span>
          </div>
          <p className="mt-1.5 text-[13px] font-medium leading-snug text-zinc-100">
            万达影城《复仇者联盟》
          </p>
          <p className="mt-2 text-[12px] text-amber-300/90">正在出票...</p>
        </article>
      </div>
    </aside>
  )
}

function SpotlightInput() {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pb-6 pt-16">
      <div className="pointer-events-auto w-full max-w-[min(50vw,720px)] min-w-[min(100%,280px)]">
        <div className="flex items-center gap-3 rounded-2xl border border-white/[0.12] bg-[#161616]/95 px-4 py-3 shadow-[0_24px_80px_rgba(0,0,0,0.75),0_0_0_1px_rgba(255,255,255,0.04)_inset] backdrop-blur-xl">
          <Sparkles
            className="size-5 shrink-0 text-amber-300 drop-shadow-[0_0_12px_rgba(251,191,36,0.45)]"
            strokeWidth={1.5}
          />
          <input
            type="text"
            readOnly
            placeholder="输入新需求，例如：把晚上电影换成去听脱口秀"
            className="min-w-0 flex-1 bg-transparent text-[14px] text-zinc-200 placeholder:text-zinc-600 focus:outline-none"
          />
          <kbd className="hidden shrink-0 rounded-md border border-white/10 bg-black/40 px-2 py-1 font-mono text-[10px] text-zinc-500 sm:inline">
            ⌘K
          </kbd>
        </div>
        <p className="mt-2 text-center font-mono text-[10px] uppercase tracking-[0.28em] text-zinc-600">
          Command palette · replan
        </p>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <div className="relative min-h-[100dvh] w-full bg-[#121212] text-zinc-300">
      {/* subtle vignette */}
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(255,255,255,0.04),transparent_55%)]"
        aria-hidden
      />

      <div className="relative mx-auto flex h-[100dvh] max-w-[1600px] flex-col gap-6 px-4 pb-28 pt-5 sm:px-6 lg:flex-row lg:gap-8 lg:px-8 lg:pb-28 lg:pt-7">
        {/* Left ~65% */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col lg:w-[65%] lg:flex-none lg:max-w-[65%]">
          <AgentExecutionPanel />
        </div>

        {/* Right ~35% */}
        <div className="flex min-h-0 w-full shrink-0 flex-col lg:mt-0 lg:w-[35%] lg:flex-none lg:max-w-[35%]">
          <TimelineSidebar />
        </div>
      </div>

      <SpotlightInput />
    </div>
  )
}
