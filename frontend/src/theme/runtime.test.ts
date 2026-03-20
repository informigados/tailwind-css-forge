import { afterEach, describe, expect, it, vi } from "vitest";

import { applyThemePreference, cleanupThemePreference } from "theme/runtime";

describe("theme runtime", () => {
  afterEach(() => {
    cleanupThemePreference();
    delete document.documentElement.dataset.theme;
    document.documentElement.style.colorScheme = "";
    vi.restoreAllMocks();
  });

  it("applies the explicit light theme immediately", () => {
    applyThemePreference("light");

    expect(document.documentElement.dataset.theme).toBe("light");
    expect(document.documentElement.style.colorScheme).toBe("light");
  });

  it("resolves the system theme from matchMedia", () => {
    const addEventListener = vi.fn();
    const removeEventListener = vi.fn();
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({
      matches: true,
      addEventListener,
      removeEventListener,
    }));

    applyThemePreference("system");

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(addEventListener).toHaveBeenCalledWith("change", expect.any(Function));
  });
});
