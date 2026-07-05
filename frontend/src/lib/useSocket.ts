"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

type Status = "connecting" | "ready" | "thinking" | "speaking" | "error" | "closed";

export interface SocketState {
  status: Status;
  transcript: string;
  answer: string;
  error: string;
  /** Send a captured frame plus either recorded audio or a client transcript. */
  ask: (imageB64: string, payload: { audioB64?: string; transcript?: string }) => void;
}

export function useSocket(): SocketState {
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<Status>("connecting");
  const [transcript, setTranscript] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
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
    (imageB64: string, payload: { audioB64?: string; transcript?: string }) => {
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
        })
      );
    },
    []
  );

  return { status, transcript, answer, error, ask };
}

function playAudio(b64: string, mime: string, onEnd: () => void) {
  const audio = new Audio(`data:${mime};base64,${b64}`);
  audio.onended = onEnd;
  audio.onerror = onEnd;
  audio.play().catch(onEnd);
}
