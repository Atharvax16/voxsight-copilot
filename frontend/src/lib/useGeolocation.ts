"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { LatLng } from "./useSocket";

/**
 * Wraps the browser Geolocation API for walk mode. Location is used transiently
 * — nothing is persisted here — and only after the user explicitly enables it
 * (which triggers the browser's own permission prompt). While enabled, every
 * position update is handed to `onUpdate` so the caller can stream it to the
 * backend's active route.
 */
export function useGeolocation(onUpdate: (loc: LatLng) => void) {
  const [enabled, setEnabled] = useState(false);
  const [error, setError] = useState("");
  const [location, setLocation] = useState<LatLng | null>(null);
  const watchRef = useRef<number | null>(null);

  // Keep the latest callback without re-subscribing the watch.
  const cbRef = useRef(onUpdate);
  cbRef.current = onUpdate;

  const clear = useCallback(() => {
    if (watchRef.current !== null) {
      navigator.geolocation.clearWatch(watchRef.current);
      watchRef.current = null;
    }
  }, []);

  const enable = useCallback(() => {
    if (typeof navigator === "undefined" || !("geolocation" in navigator)) {
      setError("Location isn't available on this device.");
      return;
    }
    setError("");
    setEnabled(true);
    watchRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setLocation(loc);
        cbRef.current(loc);
      },
      (err) => setError(err.message || "Couldn't get your location."),
      { enableHighAccuracy: true, maximumAge: 2000, timeout: 15000 }
    );
  }, []);

  const disable = useCallback(() => {
    clear();
    setEnabled(false);
  }, [clear]);

  useEffect(() => clear, [clear]); // stop watching on unmount

  return { enabled, error, location, enable, disable };
}
