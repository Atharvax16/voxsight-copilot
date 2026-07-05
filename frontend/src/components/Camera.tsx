"use client";

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";

export interface CameraHandle {
  /** Grab the current video frame as a base64 JPEG data URL. */
  captureFrame: () => string;
}

/**
 * Live rear-camera preview. Exposes captureFrame() so the parent can grab the
 * current frame at the moment the user asks a question.
 */
export const Camera = forwardRef<CameraHandle>(function Camera(_props, ref) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stream: MediaStream | null = null;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (e) {
        setError("Camera access denied or unavailable.");
      }
    })();
    return () => stream?.getTracks().forEach((t) => t.stop());
  }, []);

  useImperativeHandle(ref, () => ({
    captureFrame() {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas) return "";
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext("2d");
      if (!ctx) return "";
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL("image/jpeg", 0.7);
    },
  }));

  return (
    <div className="relative w-full overflow-hidden rounded-2xl bg-black">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="h-full w-full object-cover"
      />
      <canvas ref={canvasRef} className="hidden" />
      {error && (
        <div className="absolute inset-0 flex items-center justify-center p-4 text-center text-sm text-red-300">
          {error}
        </div>
      )}
    </div>
  );
});
