"use client";

import { useRef } from "react";
import { Camera, CameraHandle } from "@/components/Camera";
import { Mic } from "@/components/Mic";
import { useSocket } from "@/lib/useSocket";
import { useGeolocation } from "@/lib/useGeolocation";

const STATUS_LABEL: Record<string, string> = {
  connecting: "Connecting…",
  ready: "Ready — hold the button and ask",
  thinking: "Looking…",
  speaking: "Answering…",
  error: "Something went wrong",
  closed: "Disconnected",
};

export default function Home() {
  const cameraRef = useRef<CameraHandle>(null);
  const { status, transcript, answer, error, navStep, ask, sendLocation } =
    useSocket();
  const geo = useGeolocation(sendLocation);

  const sttMode =
    (process.env.NEXT_PUBLIC_STT_MODE as "browser" | "backend") ?? "browser";

  function handleSubmit(payload: { audioB64?: string; transcript?: string }) {
    const frame = cameraRef.current?.captureFrame() ?? "";
    // Attach the current position so "take me to…" / "where am I" resolve nearby.
    ask(frame, { ...payload, location: geo.location ?? undefined });
  }

  const busy = status === "thinking" || status === "speaking";

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col gap-6 bg-neutral-950 p-5 text-white">
      <header>
        <h1 className="text-3xl font-black tracking-tight">VoxSight</h1>
        <p className="text-sm text-neutral-400">
          Point the camera, hold the button, and ask about your surroundings — or
          say “take me to…” for walking directions.
        </p>
      </header>

      <div className="aspect-[3/4] w-full">
        <Camera ref={cameraRef} />
      </div>

      <div
        aria-live="polite"
        className={`rounded-lg px-4 py-3 text-center text-sm font-medium ${
          status === "error" ? "bg-red-950 text-red-200" : "bg-neutral-800 text-neutral-200"
        }`}
      >
        {error || STATUS_LABEL[status] || status}
      </div>

      {/* Navigation / walk mode: opt-in location sharing + turn-by-turn readout. */}
      <div className="rounded-lg bg-neutral-900 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">Navigation</p>
            <p className="text-xs text-neutral-400">
              {geo.enabled ? "Location on" : "Off — enable to get directions"}
            </p>
          </div>
          <button
            type="button"
            onClick={geo.enabled ? geo.disable : geo.enable}
            aria-pressed={geo.enabled}
            className={`rounded-full px-4 py-2 text-sm font-bold transition ${
              geo.enabled
                ? "bg-emerald-500 text-black"
                : "bg-white text-black active:scale-95"
            }`}
          >
            {geo.enabled ? "Location on" : "Enable navigation"}
          </button>
        </div>
        {geo.error && <p className="mt-2 text-xs text-red-300">{geo.error}</p>}
        {navStep && (
          <p aria-live="assertive" className="mt-3 text-sm font-medium text-emerald-300">
            ➜ {navStep}
          </p>
        )}
        <p className="mt-3 text-[11px] leading-snug text-neutral-500">
          Directions are advisory and can be wrong or delayed. Keep using your cane
          or guide dog — VoxSight helps you decide, it doesn’t watch the road for you.
        </p>
      </div>

      {(transcript || answer) && (
        <div className="space-y-2 rounded-lg bg-neutral-900 p-4 text-sm">
          {transcript && (
            <p className="text-neutral-400">
              <span className="font-semibold text-neutral-300">You:</span> {transcript}
            </p>
          )}
          {answer && (
            <p className="text-neutral-100">
              <span className="font-semibold">VoxSight:</span> {answer}
            </p>
          )}
        </div>
      )}

      <div className="mt-auto flex justify-center pb-4">
        <Mic
          onSubmit={handleSubmit}
          mode={sttMode}
          disabled={status === "connecting" || busy}
        />
      </div>
    </main>
  );
}
