"use client";

import { useRef } from "react";
import { Camera, CameraHandle } from "@/components/Camera";
import { Mic } from "@/components/Mic";
import { useSocket } from "@/lib/useSocket";

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
  const { status, transcript, answer, error, ask } = useSocket();

  const sttMode =
    (process.env.NEXT_PUBLIC_STT_MODE as "browser" | "backend") ?? "browser";

  function handleSubmit(payload: { audioB64?: string; transcript?: string }) {
    const frame = cameraRef.current?.captureFrame() ?? "";
    ask(frame, payload);
  }

  const busy = status === "thinking" || status === "speaking";

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col gap-6 bg-neutral-950 p-5 text-white">
      <header>
        <h1 className="text-3xl font-black tracking-tight">VoxSight</h1>
        <p className="text-sm text-neutral-400">
          Point the camera, hold the button, and ask about your surroundings.
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
