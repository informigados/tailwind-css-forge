import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "app/layout/AppShell";
import { I18nContext } from "i18n/I18nProvider";
import { translate } from "i18n/runtime";

describe("AppShell", () => {
  it("renders english navigation and shell copy when locale is en-US", () => {
    render(
      <I18nContext.Provider
        value={{
          locale: "en-US",
          theme: "system",
          setLocale: vi.fn(),
          setTheme: vi.fn(),
          t: (key, values) => translate(key, values, "en-US"),
        }}
      >
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route path="/" element={<AppShell />}>
              <Route index element={<div>content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </I18nContext.Provider>,
    );

    expect(screen.getByRole("link", { name: /Dashboard/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Import/ })).toBeInTheDocument();
    expect(screen.getByText("Turn Tailwind chaos into a controlled pipeline.")).toBeInTheDocument();
    expect(screen.getByText("content")).toBeInTheDocument();
  });
});
