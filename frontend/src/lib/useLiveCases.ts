"use client";

import { useEffect, useRef, useState } from "react";
import { WS_URL, fetchCases } from "./api";
import { IncidentCase } from "./types";

const RECONNECT_DELAY_MS = 2000;

export function useLiveCases() {
  const [cases, setCases] = useState<Record<string, IncidentCase>>({});
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const initial: IncidentCase[] = await fetchCases(50);
        if (cancelled) return;
        setCases(Object.fromEntries(initial.map((c) => [c.id, c])));
      } catch {
        // socket loop below will populate once the backend is reachable
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      socket = new WebSocket(WS_URL);
      wsRef.current = socket;

      socket.onopen = () => setConnected(true);
      socket.onclose = () => {
        setConnected(false);
        if (!cancelled) reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };
      socket.onerror = () => socket?.close();

      socket.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (
          msg.type === "case_opened" ||
          msg.type === "case_updated" ||
          msg.type === "case_resolved"
        ) {
          const c: IncidentCase = msg.data;
          setCases((prev) => ({ ...prev, [c.id]: c }));
        }
      };
    };

    connect();
    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  const list = Object.values(cases).sort(
    (a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
  );

  return { cases: list, connected };
}
