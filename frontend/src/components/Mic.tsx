"use client";

import { useEffect, useRef, useState } from "react";

interface MicProps {
  /** Fired when the user finishes asking. Provides audio (backend mode) or a
   *  transcript (browser mode). */
  onSubmit: (payload: { audioB64?: string; transcript?: string }) => void;
  disabled?: boolean;
  /** "browser" = Web Speech API (free, no keys). "backend" = record + send audio. */
  mode?: "browser" | "backend";
}

/**
 * Big press-and-hold "Ask" button. Hold to record your question, release to send.
 * Push-to-talk is more reliable for a demo than voice-activity detection.
 */
export function Mic({ onSubmit, disabled, mode = "browser" }: MicProps) {
  const [recording, setRecording] = useState(false);
  const [supported, setSupported] = useState(true);

  // Effective mode: fall back to backend recording if browser STT is unavailable.
  const effectiveMode = mode === "browser" && supported ? "browser" : "backend";

  // --- browser mode (Web Speech API) ---
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const transcriptRef = useRef("");

  // --- backend mode (MediaRecorder) ---
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    if (mode === "browser") {
      const Ctor =
        typeof window !== "undefined"
          ? window.SpeechRecognition || window.webkitSpeechRecognition
          : undefined;
      setSupported(!!Ctor);
    }
  }, [mode]);

  async function start() {
    if (disabled || recording) return;
    if (effectiveMode === "browser") startBrowser();
    else await startBackend();
  }

  function stop() {
    if (!recording) return;
    if (effectiveMode === "browser") recognitionRef.current?.stop();
    else recorderRef.current?.stop();
    setRecording(false);
  }

  function startBrowser() {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) return;
    const rec = new Ctor();
    rec.lang = "en-US";
    rec.interimResults = true;
    rec.continuous = false;
    transcriptRef.current = "";
    rec.onresult = (e) => {
      let text = "";
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
      transcriptRef.current = text.trim();
    };
    rec.onend = () => {
      const t = transcriptRef.current;
      if (t) onSubmit({ transcript: t });
    };
    rec.onerror = () => setRecording(false);
    recognitionRef.current = rec;
    rec.start();
    setRecording(true);
  }

  async function startBackend() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const b64 = await blobToBase64(blob);
        onSubmit({ audioB64: b64 });
        streamRef.current?.getTracks().forEach((t) => t.stop());
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
    } catch {
      // mic denied — status line will reflect not-ready
    }
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        disabled={disabled}
        onPointerDown={start}
        onPointerUp={stop}
        onPointerLeave={stop}
        className={`h-40 w-40 select-none rounded-full text-2xl font-bold shadow-lg transition
          ${recording ? "scale-110 bg-red-500 text-white" : "bg-white text-black active:scale-95"}
          disabled:cursor-not-allowed disabled:opacity-40`}
      >
        {recording ? "Listening…" : "Hold to Ask"}
      </button>
      <span className="text-xs text-neutral-500">
        {effectiveMode === "browser" ? "browser speech-to-text" : "recording audio"}
      </span>
    </div>
  );
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      resolve(result.split(",")[1] ?? "");
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
