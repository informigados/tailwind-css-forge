import { DEFAULT_LOCALE, FALLBACK_LOCALE, SUPPORTED_LOCALES, messages, type Locale } from "i18n/catalog";

const LOCALE_STORAGE_KEY = "forge.locale";

let activeLocale: Locale = loadStoredLocale();

function loadStoredLocale(): Locale {
  if (typeof window === "undefined") {
    return DEFAULT_LOCALE;
  }
  return normalizeLocale(window.localStorage.getItem(LOCALE_STORAGE_KEY));
}

export function normalizeLocale(value: string | null | undefined): Locale {
  if (value && SUPPORTED_LOCALES.includes(value as Locale)) {
    return value as Locale;
  }
  return DEFAULT_LOCALE;
}

export function getActiveLocale(): Locale {
  return activeLocale;
}

export function setActiveLocale(locale: string): Locale {
  activeLocale = normalizeLocale(locale);
  if (typeof window !== "undefined") {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, activeLocale);
  }
  if (typeof document !== "undefined") {
    document.documentElement.lang = activeLocale;
  }
  return activeLocale;
}

export function translate(
  key: string,
  values?: Record<string, string | number>,
  locale: string = activeLocale,
): string {
  const normalizedLocale = normalizeLocale(locale);
  const entry =
    messages[normalizedLocale][key] ??
    messages[FALLBACK_LOCALE][key] ??
    messages[DEFAULT_LOCALE][key];

  if (!entry) {
    return key;
  }
  if (typeof entry === "function") {
    return entry(values);
  }
  if (!values) {
    return entry;
  }
  return entry.replace(/\{(\w+)\}/g, (_match, token) => String(values[token] ?? `{${token}}`));
}
