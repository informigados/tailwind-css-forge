export type ThemePreference = "system" | "dark" | "light";
export type ResolvedTheme = "dark" | "light";

let activeCleanup: (() => void) | null = null;

function resolveSystemTheme(mediaQuery?: MediaQueryList): ResolvedTheme {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return "dark";
  }
  const resolvedQuery = mediaQuery ?? window.matchMedia("(prefers-color-scheme: dark)");
  return resolvedQuery.matches ? "dark" : "light";
}

function applyResolvedTheme(theme: ResolvedTheme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

export function applyThemePreference(theme: string): ThemePreference {
  const normalized: ThemePreference = theme === "light" || theme === "dark" ? theme : "system";

  activeCleanup?.();
  activeCleanup = null;

  if (normalized === "system" && typeof window !== "undefined" && typeof window.matchMedia === "function") {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const sync = () => applyResolvedTheme(resolveSystemTheme(mediaQuery));
    sync();
    mediaQuery.addEventListener("change", sync);
    activeCleanup = () => mediaQuery.removeEventListener("change", sync);
    return normalized;
  }

  applyResolvedTheme(normalized === "light" ? "light" : "dark");
  return normalized;
}

export function cleanupThemePreference() {
  activeCleanup?.();
  activeCleanup = null;
}
