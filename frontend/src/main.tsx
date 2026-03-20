import React from "react";
import ReactDOM from "react-dom/client";

import { AppRouter } from "app/router/AppRouter";
import { I18nProvider } from "i18n/I18nProvider";
import "styles/app.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <I18nProvider>
      <AppRouter />
    </I18nProvider>
  </React.StrictMode>,
);
