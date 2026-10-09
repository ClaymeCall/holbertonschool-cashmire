// jsdom (used by `test.environment: "jsdom"` in vite.config.js) has no
// layout engine, so it doesn't implement these — but LayerChart (our charts
// dependency) calls them unconditionally while mounting an SVG chart.
// Without a polyfill, every chart-rendering test throws immediately. These
// are dumb stand-ins (zero size), good enough since our component tests
// assert on our own legend/text markup, never on actual pixel geometry.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

if (typeof globalThis.matchMedia === "undefined") {
  globalThis.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() {
      return false;
    },
  });
}

if (typeof SVGElement !== "undefined") {
  if (!SVGElement.prototype.getBBox) {
    SVGElement.prototype.getBBox = () => ({ x: 0, y: 0, width: 0, height: 0 });
  }
  if (!SVGElement.prototype.getComputedTextLength) {
    SVGElement.prototype.getComputedTextLength = () => 0;
  }
}
