import { createContext, useEffect, useState, type ReactNode } from "react";

import type { Locale } from "i18n/catalog";
import { getActiveLocale, setActiveLocale, translate } from "i18n/runtime";
import { applyThemePreference, cleanupThemePreference, type ThemePreference } from "theme/runtime";
import { api } from "services/api";

type I18nContextValue = {
  locale: Locale;
  theme: ThemePreference;
  setLocale: (locale: string) => void;
  setTheme: (theme: ThemePreference) => void;
  t: (key: string, values?: Record<string, string | number>) => string;
};

export const I18nContext = createContext<I18nContextValue>({
  locale: getActiveLocale(),
  theme: "system",
  setLocale: setActiveLocale,
  setTheme: applyThemePreference,
  t: (key, values) => translate(key, values),
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(getActiveLocale());
  const [theme, setThemeState] = useState<ThemePreference>(() => applyThemePreference("system"));

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  useEffect(() => {
    let active = true;
    api
      .getSettings()
      .then((settings) => {
        if (!active) {
          return;
        }
        setLocaleState(setActiveLocale(settings.language));
        setThemeState(applyThemePreference(settings.theme));
      })
      .catch(() => {
        if (active) {
          document.documentElement.lang = locale;
        }
      });
    return () => {
      active = false;
      cleanupThemePreference();
    };
  }, []);

  function handleSetLocale(nextLocale: string) {
    setLocaleState(setActiveLocale(nextLocale));
  }

  function handleSetTheme(nextTheme: ThemePreference) {
    setThemeState(applyThemePreference(nextTheme));
  }

  return (
    <I18nContext.Provider
      value={{
        locale,
        theme,
        setLocale: handleSetLocale,
        setTheme: handleSetTheme,
        t: (key, values) => translate(key, values, locale),
      }}
    >
      {children}
    </I18nContext.Provider>
  );
}
