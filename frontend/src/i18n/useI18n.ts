import { useContext } from "react";

import { I18nContext } from "i18n/I18nProvider";

export function useI18n() {
  return useContext(I18nContext);
}
