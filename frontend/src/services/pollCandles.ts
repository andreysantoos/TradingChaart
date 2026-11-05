// A separate lifecycle for each symbol/timeframe; late responses cannot commit.
export function pollCandles<T>(options: {
  fetch: (signal: AbortSignal) => Promise<T>;
  onData: (data: T) => void;
  onError: () => void;
  onLoading: (loading: boolean) => void;
  intervalMs?: number;
}) {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  async function refresh() {
    options.onLoading(true);
    try {
      const data = await options.fetch(controller.signal);
      if (!controller.signal.aborted) options.onData(data);
    } catch {
      if (!controller.signal.aborted) options.onError();
    } finally {
      if (!controller.signal.aborted) {
        options.onLoading(false);
        timer = setTimeout(refresh, options.intervalMs ?? 60000);
      }
    }
  }
  void refresh();
  return () => {
    controller.abort();
    clearTimeout(timer);
  };
}
