import { useEffect, useState } from "react"

export interface GeolocationState {
  lat: number | null
  lng: number | null
  loading: boolean
  error: string | null
  permissionDenied: boolean
}

export function useGeolocation(): GeolocationState {
  const [state, setState] = useState<GeolocationState>({
    lat: null,
    lng: null,
    loading: true,
    error: null,
    permissionDenied: false,
  })

  useEffect(() => {
    if (!("geolocation" in navigator)) {
      setState({
        lat: null,
        lng: null,
        loading: false,
        error: "浏览器不支持地理位置",
        permissionDenied: false,
      })
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setState({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          loading: false,
          error: null,
          permissionDenied: false,
        })
      },
      (err) => {
        setState({
          lat: null,
          lng: null,
          loading: false,
          error: err.message,
          permissionDenied: err.code === err.PERMISSION_DENIED,
        })
      },
      {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 300000, // 5 min cache
      },
    )
  }, [])

  return state
}
