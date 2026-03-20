import { getActiveLocale, translate } from "i18n/runtime";

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return translate("common.notAvailable");
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(getActiveLocale(), {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

export function formatDuration(durationMs: number | null | undefined): string {
  if (!durationMs || durationMs < 0) {
    return translate("common.notAvailable");
  }

  if (durationMs < 1000) {
    return `${durationMs} ms`;
  }

  return `${(durationMs / 1000).toFixed(2)} s`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "0%";
  }

  return new Intl.NumberFormat(getActiveLocale(), {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(value);
}
