import { expect, test } from "@playwright/test";

test("dashboard renders in english when locale is en-US", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("forge.locale", "en-US");
  });

  await page.route("**/api/settings", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        settings: {
          language: "en-US",
          theme: "system",
          default_workspace_path: "",
          default_exports_path: "",
          backup_before_build: true,
          default_minify: true,
          detailed_logs: true,
          build_timeout_seconds: 600,
        },
      }),
    });
  });

  await page.route("**/api/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        app: "Tailwind CSS Forge",
        environment: "test",
        version: "0.1.0",
      }),
    });
  });

  await page.route("**/api/projects", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
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
      ]),
    });
  });

  await page.goto("/");

  await expect(page.getByRole("link", { name: /Dashboard/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /^Import \/$/ })).toBeVisible();
  await expect(page.getByText("Recent projects")).toBeVisible();
  await expect(page.getByText(/^Demo$/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Open analysis" })).toBeVisible();
});
