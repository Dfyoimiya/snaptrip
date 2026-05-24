import { AlertFeed } from "../../components/monitor/AlertFeed"
import { WeatherPanel } from "../../components/monitor/WeatherPanel"
import { TrafficPanel } from "../../components/monitor/TrafficPanel"
import { PeakPanel } from "../../components/monitor/PeakPanel"
import { MonitorConfig } from "../../components/monitor/MonitorConfig"

export function MonitorTab() {
  return (
    <div className="h-full overflow-auto bg-zinc-950">
      <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left column */}
        <div className="space-y-4">
          <AlertFeed />
          <MonitorConfig />
        </div>
        {/* Right column */}
        <div className="space-y-4">
          <WeatherPanel />
          <TrafficPanel />
          <PeakPanel />
        </div>
      </div>
    </div>
  )
}
