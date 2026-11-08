/**
 * Colours for chart marks. SVG presentation attributes cannot reliably read CSS variables, so the
 * PRD 7.2 values used by charts are repeated here. Each palette was checked with the
 * data-visualisation palette validator (lightness, chroma, colour-blind separation, contrast).
 */

/** One series, or a single categorical axis whose labels already identify each bar. */
export const SERIES_PRIMARY = "#2563EB";

/** A second series beside SERIES_PRIMARY. The pair passes every validator check. */
export const SERIES_SECONDARY = "#D97706";

/** Contributions: raises the score versus lowers it. The pair passes every validator check. */
export const RAISES_SCORE = "#B91C1C";
export const LOWERS_SCORE = "#2563EB";

/** Recessive structure: grid lines, axes and reference lines. */
export const GRID = "#E2E8F0";
export const AXIS_TEXT = "#64748B";
export const REFERENCE = "#172033";
