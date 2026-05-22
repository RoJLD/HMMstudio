/** Browser-native SVG export utilities.
 *
 * We DON'T use a third-party library. The SVG is already in the DOM as a
 * mounted React Flow / hand-rolled SVG; we just clone the node, inline any
 * computed font styles (so the downloaded file renders correctly when opened
 * standalone), and trigger a `<a download>` click.
 *
 * For PNG export users can open the SVG in any browser → "Save As" image,
 * or use Inkscape / Illustrator. Native PNG would need a canvas roundtrip
 * which can be added later without breaking this API.
 */

/** Serialize an SVG element to a standalone SVG string. */
export function svgToString(svg: SVGSVGElement): string {
  const clone = svg.cloneNode(true) as SVGSVGElement;

  // Ensure xmlns is set so file opens standalone
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  if (!clone.getAttribute("xmlns:xlink")) {
    clone.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
  }

  // Inline a couple of essential computed styles. Tailwind classes are applied
  // via stylesheets that won't be present in the downloaded file. We copy the
  // most-visible ones (fill, stroke, font) from the live tree.
  inlineComputedStyles(svg, clone);

  // Ensure width/height are present (some browsers omit them on inline SVG)
  if (!clone.getAttribute("width")) {
    const rect = svg.getBoundingClientRect();
    clone.setAttribute("width", String(Math.round(rect.width)));
    clone.setAttribute("height", String(Math.round(rect.height)));
  }

  const serializer = new XMLSerializer();
  return '<?xml version="1.0" encoding="UTF-8"?>\n' + serializer.serializeToString(clone);
}

/** Walk both trees in parallel, copying key computed styles onto the clone. */
function inlineComputedStyles(live: Element, clone: Element): void {
  const liveStyle = window.getComputedStyle(live);
  const target = clone as HTMLElement;
  const keys = [
    "fill",
    "stroke",
    "stroke-width",
    "stroke-dasharray",
    "font-family",
    "font-size",
    "font-weight",
    "text-anchor",
    "opacity",
    "fill-opacity",
    "stroke-opacity",
  ];
  for (const k of keys) {
    const v = liveStyle.getPropertyValue(k);
    if (v && v !== "" && v !== "none") {
      target.style.setProperty(k, v);
    }
  }
  const liveChildren = Array.from(live.children);
  const cloneChildren = Array.from(clone.children);
  for (let i = 0; i < liveChildren.length && i < cloneChildren.length; i++) {
    inlineComputedStyles(liveChildren[i], cloneChildren[i]);
  }
}

/** Trigger a download of the given SVG element. */
export function downloadSvg(svg: SVGSVGElement, filename: string): void {
  const text = svgToString(svg);
  const blob = new Blob([text], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".svg") ? filename : `${filename}.svg`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Revoke after a short delay so the click handler completes
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
