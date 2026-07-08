"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** WS endpoint. If NEXT_PUBLIC_WS_URL isn't set (e.g. the static build served by
 *  the backend behind one tunnel), derive it from the current origin so it works
 *  same-origin over http or https. */
function resolveWsUrl(): string {
  const env = process.env.NEXT_PUBLIC_WS_URL;
  if (env) return env;
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}/ws`;
  }
  return "ws://localhost:8000/ws";
}

type Status = "connecting" | "ready" | "thinking" | "speaking" | "error" | "closed";

export interface LatLng {
  lat: number;
  lng: number;
}

export interface SocketState {
  status: Status;
  transcript: string;
  answer: string;
  error: string;
  /** Latest turn-by-turn navigation instruction, if any. */
  navStep: string;
  /** Send a captured frame plus either recorded audio or a client transcript.
   *  `location` lets navigation commands ("take me to…") resolve nearby. */
  ask: (
    imageB64: string,
    payload: { audioB64?: string; transcript?: string; location?: LatLng }
  ) => void;
  /** Walk-mode heartbeat: push the current position so the active route can
   *  announce the next maneuver. No model call — cheap to send often. */
  sendLocation: (loc: LatLng) => void;
}

export function useSocket(): SocketState {
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<Status>("connecting");
  const [transcript, setTranscript] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [navStep, setNavStep] = useState("");

  useEffect(() => {
    const ws = new WebSocket(resolveWsUrl());
    wsRef.current = ws;

    ws.onopen = () => setStatus("ready");
    ws.onclose = () => setStatus("closed");
    ws.onerror = () => {
      setStatus("error");
      setError("Could not reach the backend. Is it running on :8000?");
    };
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "transcript") setTranscript(msg.text);
      else if (msg.type === "answer") {
        setAnswer(msg.text);
        setStatus("speaking");
      } else if (msg.type === "nav_step") {
        setNavStep(msg.text);
      } else if (msg.type === "audio") {
        playAudio(msg.data, msg.mime, () => setStatus("ready"));
      } else if (msg.type === "error") {
        setError(msg.message);
        setStatus("error");
      }
    };

    return () => ws.close();
  }, []);

  const ask = useCallback(
    (
      imageB64: string,
      payload: { audioB64?: string; transcript?: string; location?: LatLng }
    ) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      setTranscript(payload.transcript ?? "");
      setAnswer("");
      setError("");
      setStatus("thinking");
      ws.send(
        JSON.stringify({
          type: "query",
          image: imageB64,
          audio: payload.audioB64 ?? "",
          transcript: payload.transcript ?? "",
          location: payload.location,
        })
      );
    },
    []
  );

  const sendLocation = useCallback((loc: LatLng) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "location", location: loc }));
  }, []);

  return { status, transcript, answer, error, navStep, ask, sendLocation };
}

function playAudio(b64: string, mime: string, onEnd: () => void) {
  const audio = new Audio(`data:${mime};base64,${b64}`);
  audio.onended = onEnd;
  audio.onerror = onEnd;
  audio.play().catch(onEnd);
}
