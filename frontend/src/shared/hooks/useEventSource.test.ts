import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useEventSource } from "@/shared/hooks/useEventSource";

type Listener = (message: { data: string; lastEventId: string }) => void;

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  listeners = new Map<string, Listener>();
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(name: string, listener: Listener) {
    this.listeners.set(name, listener);
  }

  removeEventListener(name: string) {
    this.listeners.delete(name);
  }

  close() {
    this.closed = true;
  }

  emit(name: string, data: string, lastEventId: string) {
    this.listeners.get(name)?.({ data, lastEventId });
  }
}

describe("useEventSource", () => {
  it("opens the exact URL with no token attached", () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    FakeEventSource.instances = [];
    const { result } = renderHook(() => useEventSource("/api/tasks/t1/events"));
    const source = FakeEventSource.instances[0];
    expect(source.url).toBe("/api/tasks/t1/events");
    expect(source.url).not.toContain("token");
    act(() => {
      source.onopen?.();
    });
    expect(result.current.status).toBe("open");
    vi.unstubAllGlobals();
  });

  it("appends typed events and tracks the last id", () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    FakeEventSource.instances = [];
    const { result } = renderHook(() => useEventSource<{ seq: number }>("/api/tasks/t1/events"));
    const source = FakeEventSource.instances[0];
    act(() => {
      source.emit("audit", JSON.stringify({ seq: 1 }), "1");
      source.emit("audit", JSON.stringify({ seq: 2 }), "2");
    });
    expect(result.current.events).toEqual([{ seq: 1 }, { seq: 2 }]);
    expect(result.current.lastEventId).toBe("2");
    vi.unstubAllGlobals();
  });

  it("closes the stream on unmount", () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    FakeEventSource.instances = [];
    const { unmount } = renderHook(() => useEventSource("/api/tasks/t1/events"));
    const source = FakeEventSource.instances[0];
    unmount();
    expect(source.closed).toBe(true);
    vi.unstubAllGlobals();
  });

  it("stays shut without a URL", () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    FakeEventSource.instances = [];
    const { result } = renderHook(() => useEventSource(null));
    expect(FakeEventSource.instances).toHaveLength(0);
    expect(result.current.status).toBe("closed");
    vi.unstubAllGlobals();
  });
});
