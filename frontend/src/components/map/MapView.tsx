import { useEffect, useMemo } from "react"
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import { usePlanStore } from "../../stores/planStore"

// Fix Leaflet default marker icons in bundlers
import iconUrl from "leaflet/dist/images/marker-icon.png"
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png"
import shadowUrl from "leaflet/dist/images/marker-shadow.png"

// Workaround: set default icon globally
const DefaultIcon = L.icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})
L.Marker.prototype.options.icon = DefaultIcon

// Colored markers for different slot indices
const SLOT_COLORS = ["#f43f5e", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ec4899"]

function createColoredIcon(index: number) {
  const color = SLOT_COLORS[index % SLOT_COLORS.length]
  return L.divIcon({
    className: "",
    html: `<div style="
      width:28px;height:28px;border-radius:50%;
      background:${color};border:2px solid #fff;
      display:flex;align-items:center;justify-content:center;
      font-size:11px;font-weight:bold;color:#fff;
      box-shadow:0 2px 6px rgba(0,0,0,0.4);
    ">${index + 1}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
  })
}

function FitBounds() {
  const slots = usePlanStore((s) => s.slots)
  const map = useMap()

  useEffect(() => {
    if (slots.length === 0) return
    const bounds = L.latLngBounds(
      slots.map((s) => [s.poi.lat, s.poi.lng] as [number, number]),
    )
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40] })
    }
  }, [slots, map])

  return null
}

export function MapView() {
  const slots = usePlanStore((s) => s.slots)

  // Default center: Beijing
  const center: [number, number] = useMemo(() => {
    if (slots.length > 0) return [slots[0].poi.lat, slots[0].poi.lng]
    return [39.9219, 116.4435]
  }, [slots])

  const routePositions: [number, number][] = useMemo(
    () => slots.map((s) => [s.poi.lat, s.poi.lng] as [number, number]),
    [slots],
  )

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      <div className="px-4 py-3 border-b border-zinc-800 shrink-0">
        <h2 className="text-sm font-semibold text-zinc-100">Map</h2>
      </div>
      <div className="flex-1 relative">
        <MapContainer
          center={center}
          zoom={13}
          className="h-full w-full"
          zoomControl={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds />
          {slots.map((slot, i) => (
            <Marker
              key={slot.sequence}
              position={[slot.poi.lat, slot.poi.lng]}
              icon={createColoredIcon(i)}
            >
              <Popup>
                <div className="text-xs">
                  <div className="font-semibold">{slot.poi.name}</div>
                  <div className="text-zinc-500">{slot.poi.type} · ★{slot.poi.rating}</div>
                  <div className="text-zinc-500">
                    {new Date(slot.time_range.start).toLocaleTimeString()} -{" "}
                    {new Date(slot.time_range.end).toLocaleTimeString()}
                  </div>
                  <div className="text-zinc-500">¥{slot.estimated_cost} · confidence: {(slot.confidence * 100).toFixed(0)}%</div>
                </div>
              </Popup>
            </Marker>
          ))}
          {routePositions.length > 1 && (
            <Polyline
              positions={routePositions}
              pathOptions={{ color: "#f43f5e", weight: 2, dashArray: "6 4", opacity: 0.6 }}
            />
          )}
        </MapContainer>
      </div>
    </div>
  )
}
