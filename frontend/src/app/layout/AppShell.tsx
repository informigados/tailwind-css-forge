import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useI18n } from "i18n/useI18n";

export function AppShell() {
  const { t } = useI18n();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const navigation = [
    { to: "/", label: t("nav.dashboard") },
    { to: "/projects/import", label: t("nav.import") },
    { to: "/history", label: t("nav.history") },
    { to: "/settings", label: t("nav.operation") },
  ];

  return (
    <div className="forge-shell min-h-screen">
      <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 pt-4 lg:hidden">
        <div className="flex items-center gap-3">
          <div className="forge-logo-mark h-12 w-12 font-['IBM_Plex_Mono'] text-base font-bold">
            F
          </div>
          <div>
            <p className="forge-eyebrow text-xs uppercase tracking-[0.34em]">Tailwind CSS</p>
            <p className="font-['Space_Grotesk'] text-xl font-bold">Forge</p>
          </div>
        </div>
        <button
          type="button"
          aria-expanded={isMobileMenuOpen}
          aria-controls="forge-shell-navigation"
          aria-label={isMobileMenuOpen ? t("shell.closeMenu") : t("shell.openMenu")}
          onClick={() => setIsMobileMenuOpen((current) => !current)}
          className="forge-button forge-button-secondary"
        >
          {isMobileMenuOpen ? t("shell.closeMenu") : t("shell.openMenu")}
        </button>
      </div>
      <div className="mx-auto grid min-h-screen max-w-[1600px] grid-cols-1 gap-6 px-4 py-4 lg:grid-cols-[288px_minmax(0,1fr)] lg:px-6 lg:py-6">
        <aside
          id="forge-shell-navigation"
          className={`${isMobileMenuOpen ? "block" : "hidden"} forge-sidebar rounded-[32px] p-6 lg:sticky lg:top-6 lg:block lg:self-start`}
        >
          <div className="flex items-center gap-4">
            <div className="forge-logo-mark h-14 w-14 font-['IBM_Plex_Mono'] text-lg font-bold">
              F
            </div>
            <div>
              <p className="forge-eyebrow text-xs uppercase tracking-[0.34em]">Tailwind CSS</p>
              <h1 className="font-['Space_Grotesk'] text-2xl font-bold">Forge</h1>
            </div>
          </div>

          <p className="forge-subtitle mt-6 text-sm leading-6">
            {t("shell.description")}
          </p>

          <nav className="mt-10 space-y-2" aria-label={t("shell.navigation")}>
            {navigation.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setIsMobileMenuOpen(false)}
                className={({ isActive }) =>
                  `forge-nav-link group flex items-center justify-between ${
                    isActive
                      ? "forge-nav-link-active"
                      : "forge-nav-link-idle"
                  }`
                }
              >
                <span>{item.label}</span>
                <span className="forge-tertiary font-['IBM_Plex_Mono'] text-xs">
                  /
                </span>
              </NavLink>
            ))}
          </nav>

          <div className="forge-guideline-panel mt-10 rounded-[28px] p-5">
            <p className="forge-eyebrow text-xs uppercase tracking-[0.3em]">{t("shell.guideline")}</p>
            <p className="mt-3 text-sm leading-6">
              {t("shell.guidelineText")}
            </p>
          </div>
        </aside>

        <main className="space-y-6">
          <header className="forge-header-panel rounded-[32px] p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="forge-tertiary text-xs font-semibold uppercase tracking-[0.32em]">
                  {t("shell.headerEyebrow")}
                </p>
                <h2 className="mt-3 font-['Space_Grotesk'] text-4xl font-bold leading-tight">
                  {t("shell.headerTitle")}
                </h2>
              </div>
              <div className="forge-subtle-card rounded-[24px] px-5 py-4">
                <p className="forge-tertiary text-xs uppercase tracking-[0.26em]">{t("shell.phaseFocus")}</p>
                <p className="forge-subtitle mt-2 font-['IBM_Plex_Mono'] text-sm">
                  {t("shell.phaseText")}
                </p>
              </div>
            </div>
          </header>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
