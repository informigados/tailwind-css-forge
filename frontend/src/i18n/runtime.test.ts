import { describe, expect, it } from "vitest";

import { DEFAULT_LOCALE } from "i18n/catalog";
import { normalizeLocale, setActiveLocale, translate } from "i18n/runtime";

describe("i18n runtime", () => {
  it("normalizes unsupported locales to the default locale", () => {
    expect(normalizeLocale("es-ES")).toBe(DEFAULT_LOCALE);
    expect(normalizeLocale(undefined)).toBe(DEFAULT_LOCALE);
  });

  it("translates known keys and falls back when needed", () => {
    expect(translate("nav.dashboard", undefined, "en-US")).toBe("Dashboard");
    expect(translate("nav.dashboard", undefined, "pt-BR")).toBe("Painel");
    expect(translate("unknown.key", undefined, "en-US")).toBe("unknown.key");
  });

  it("stores the active locale on the document element", () => {
    const locale = setActiveLocale("en-US");
    expect(locale).toBe("en-US");
    expect(document.documentElement.lang).toBe("en-US");
  });
});
