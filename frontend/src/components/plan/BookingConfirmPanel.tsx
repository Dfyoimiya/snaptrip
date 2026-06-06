import { confirmPlan } from "../../api/plan"
import { usePlanStore } from "../../stores/planStore"
import { useAgentStore } from "../../stores/agentStore"

export function BookingConfirmPanel() {
  const planId = usePlanStore((s) => s.planId)
  const interruptPayload = useAgentStore((s) => s.interruptPayload)
  const setInterruptPayload = useAgentStore((s) => s.setInterruptPayload)
  const setPlan = usePlanStore((s) => s.setPlan)

  // Only show for booking_confirm interrupts
  if (!interruptPayload || interruptPayload.type !== "booking_confirm") return null

  const booking = interruptPayload.booking

  async function handleConfirm(decision: string) {
    setInterruptPayload(null)
    try {
      const resp = await confirmPlan(planId, { decision })
      if (resp.code === 0 && resp.data) {
        setPlan(resp.data)
      }
    } catch {
      // ignore
    }
  }

  return (
    <div className="mx-4 mb-3 p-3 rounded-lg bg-indigo-900/60 border border-indigo-700/50 space-y-3">
      <p className="text-xs text-indigo-200">
        {interruptPayload.message || "确认以下预订？"}
      </p>

      {/* Booking orders */}
      {booking?.orders && booking.orders.length > 0 && (
        <div className="space-y-1.5 border-t border-indigo-700/50 pt-2">
          {booking.orders.map((o, i) => (
            <div key={i} className="flex gap-2 text-[10px]">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  {o.order_type && (
                    <span className="text-[9px] font-medium bg-indigo-500/30 text-indigo-200 px-1 py-0.5 rounded">
                      {o.order_type === "restaurant" ? "餐厅" : o.order_type === "activity" ? "活动" : o.order_type}
                    </span>
                  )}
                  {o.poi_name && (
                    <span className="text-indigo-100 truncate font-medium">{o.poi_name}</span>
                  )}
                </div>
                <div className="flex gap-2 mt-0.5">
                  {o.time && <span className="text-indigo-400">{o.time}</span>}
                  {o.guest_count != null && (
                    <span className="text-indigo-400">{o.guest_count}人</span>
                  )}
                  {o.amount_cny != null && (
                    <span className="text-indigo-300">¥{o.amount_cny}</span>
                  )}
                  {o.note && (
                    <span className="text-indigo-400 truncate">{o.note}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Total */}
      {booking?.total_amount != null && booking.total_amount > 0 && (
        <div className="border-t border-indigo-700/50 pt-1.5 text-[10px] text-indigo-200 flex justify-between">
          <span>合计</span>
          <span className="text-indigo-100 font-medium">¥{booking.total_amount}</span>
        </div>
      )}

      <div className="flex gap-2">
        <button
          className="flex-1 py-1.5 text-xs rounded bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
          onClick={() => handleConfirm("confirmed")}
        >
          确认预订
        </button>
        <button
          className="flex-1 py-1.5 text-xs rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-300 transition-colors"
          onClick={() => handleConfirm("rejected")}
        >
          取消
        </button>
      </div>
    </div>
  )
}
