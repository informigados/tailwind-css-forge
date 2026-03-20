import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppShell } from "app/layout/AppShell";
import { AnalysisPage } from "features/analysis/AnalysisPage";
import { BuildPage } from "features/build/BuildPage";
import { HistoryPage } from "features/history/HistoryPage";
import { HomePage } from "features/home/HomePage";
import { NotFoundPage } from "features/not-found/NotFoundPage";
import { ImportPage } from "features/projects/ImportPage";
import { PublishPage } from "features/publish/PublishPage";
import { ReportPage } from "features/reports/ReportPage";
import { SettingsPage } from "features/settings/SettingsPage";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "projects/import", element: <ImportPage /> },
      { path: "projects/:projectId/analysis", element: <AnalysisPage /> },
      { path: "projects/:projectId/build", element: <BuildPage /> },
      { path: "projects/:projectId/report", element: <ReportPage /> },
      { path: "projects/:projectId/publish", element: <PublishPage /> },
      { path: "history", element: <HistoryPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
