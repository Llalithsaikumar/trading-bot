/** Number and currency formatting utilities */
export const formatPrice = (value: string | number, decimals = 2): string =>
  Number(value).toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

export const formatPercent = (value: string | number): string =>
  `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(2)}%`;

export const formatVolume = (value: string | number): string => {
  const n = Number(value);
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(2)}K`;
  return n.toFixed(2);
};
