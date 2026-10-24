import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useAnimusStudio } from "@/lib/useAnimusStudio";

const snapshot = {
  session_id: "ast_1",
  title: "Castle",
  active_branch_id: "main",
  active_version_id: "ver_1",
  scene: { entities: [] },
};

class FakeWebSocket {
  static OPEN = 1;
  static instances: FakeWebSocket[] = [];
  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  sent: string[] = [];

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
    queueMicrotask(() => {
      this.readyState = FakeWebSocket.OPEN;
      this.onopen?.();
    });
  }

  send(payload: string) {
    this.sent.push(payload);
  }

  close() {
    this.readyState = 3;
    queueMicrotask(() => this.onclose?.());
  }

  emit(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }
}

function installWebSocket() {
  FakeWebSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeWebSocket);
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => null },
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useAnimusStudio", () => {
  it("exposes a typed load error for a missing session", async () => {
    installWebSocket();
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ detail: "unknown studio session" }, 404),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useAnimusStudio("ast_missing"));
    await waitFor(() => expect(result.current.loadError?.status).toBe(404));
    expect(result.current.loadError?.detail).toBe("unknown studio session");
    expect(result.current.loading).toBe(false);
  });

  it("refreshes when the server reports a queue overflow", async () => {
    installWebSocket();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(snapshot));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useAnimusStudio("ast_1"));
    await waitFor(() => expect(result.current.snapshot?.session_id).toBe("ast_1"));
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));

    FakeWebSocket.instances[0].emit({ type: "resync_required", reason: "queue_overflow" });
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2));
    expect(result.current.loadError).toBeNull();
  });

  it("ignores malformed websocket payloads", async () => {
    installWebSocket();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(snapshot));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useAnimusStudio("ast_1"));
    await waitFor(() => expect(result.current.snapshot).not.toBeNull());
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));

    FakeWebSocket.instances[0].onmessage?.({ data: "not json" });
    FakeWebSocket.instances[0].emit({ type: "snapshot", session: { nope: true } });
    expect(result.current.snapshot?.session_id).toBe("ast_1");
    expect(result.current.loadError).toBeNull();
  });

  it("deduplicates events and reloads immediately on a sequence gap", async () => {
    installWebSocket();
    const sequenced = { ...snapshot, last_event_seq: 5 };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(sequenced));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useAnimusStudio("ast_1"));
    await waitFor(() => expect(result.current.snapshot).not.toBeNull());
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    expect(fetchMock.mock.calls.length).toBe(1);

    const socket = FakeWebSocket.instances[0];
    socket.emit({ type: "event", event_type: "studio.intent.applied", seq: 5 });
    await new Promise((resolve) => setTimeout(resolve, 180));
    expect(fetchMock.mock.calls.length).toBe(1);

    socket.emit({ type: "event", event_type: "studio.intent.applied", seq: 6 });
    await new Promise((resolve) => setTimeout(resolve, 180));
    expect(fetchMock.mock.calls.length).toBe(2);

    socket.emit({ type: "event", event_type: "studio.intent.applied", seq: 8 });
    await new Promise((resolve) => setTimeout(resolve, 60));
    expect(fetchMock.mock.calls.length).toBe(3);
  });

  it("closes a silent socket and reconnects", async () => {
    vi.useFakeTimers();
    installWebSocket();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(snapshot));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useAnimusStudio("ast_1"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.snapshot).not.toBeNull();
    expect(FakeWebSocket.instances).toHaveLength(1);
    const first = FakeWebSocket.instances[0];
    expect(first.readyState).toBe(1);

    act(() => {
      vi.advanceTimersByTime(76_000);
    });
    expect(first.readyState).toBe(3);

    await act(async () => {
      await Promise.resolve();
    });
    act(() => {
      vi.advanceTimersByTime(2_000);
    });
    expect(FakeWebSocket.instances.length).toBeGreaterThan(1);
  });

  it("aborts an in-flight mutation on unmount", async () => {
    installWebSocket();
    let mutationSignal: AbortSignal | undefined;
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (String(url).endsWith("/undo")) {
        mutationSignal = init?.signal ?? undefined;
        return new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        });
      }
      return Promise.resolve(jsonResponse(snapshot));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { result, unmount } = renderHook(() => useAnimusStudio("ast_1"));
    await waitFor(() => expect(result.current.snapshot).not.toBeNull());

    const pending = result.current.undo();
    await waitFor(() => expect(mutationSignal).toBeDefined());
    unmount();

    expect(mutationSignal?.aborted).toBe(true);
    await pending;
  });
});
