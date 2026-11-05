export interface HorizontalZoom {
  span: number;
  offsetFromEnd: number;
}

export function captureHorizontalZoom(range: { from: number; to: number }, count: number): HorizontalZoom | null {
  const span = range.to - range.from;
  if (count <= 0 || !Number.isFinite(span) || span <= 0 || !Number.isFinite(range.to)) return null;
  return { span, offsetFromEnd: count - 1 - range.to };
}

export function restoreHorizontalZoom(zoom: HorizontalZoom, count: number) {
  if (count <= 0) return null;
  let to = count - 1 - zoom.offsetFromEnd;
  // If the saved pan is entirely outside a shorter history, show its tail.
  // Preserve the zoom width and saved preference for the next asset.
  if (to < 0 || to - zoom.span > count - 1) to = count - 1;
  return { from: to - zoom.span, to };
}
