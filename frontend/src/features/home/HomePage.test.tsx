import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HomePage } from "features/home/HomePage";
import { I18nContext } from "i18n/I18nProvider";
import type { HealthStatus, ProjectSummary } from "lib/types";
import { translate } from "i18n/runtime";
import { api } from "services/api";

describe("HomePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders imported projects and english labels", async () => {
    const health: HealthStatus = {
      status: "ok",
      app: "Tailwind CSS Forge",
      environment: "test",
      version: "0.1.0",
    };
    const projects: ProjectSummary[] = [
      {
        id: "project_123",
        name: "Demo",
        source_path: "C:/demo",
        workspace_path: "C:/workspace/demo",
        fingerprint: "abc123",
        created_at: "2026-03-19T10:00:00Z",
        updated_at: "2026-03-19T10:05:00Z",
        last_status: "built",
      },
    ];

    vi.spyOn(api, "getHealth").mockResolvedValue(health);
    vi.spyOn(api, "listProjects").mockResolvedValue(projects);

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
        <MemoryRouter>
          <HomePage />
        </MemoryRouter>
      </I18nContext.Provider>,
    );

    await waitFor(() => expect(screen.getByText("Recent projects")).toBeInTheDocument());

    expect(screen.getByText("Ready for deploy")).toBeInTheDocument();
    expect(screen.getByText("Import new project")).toBeInTheDocument();
    expect(screen.getByText("Demo")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open analysis" })).toBeInTheDocument();
  });
});
