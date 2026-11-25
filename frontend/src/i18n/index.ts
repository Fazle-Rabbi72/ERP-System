import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import bn from "@/i18n/bn.json";
import en from "@/i18n/en.json";

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    bn: { translation: bn },
  },
  lng: "en",
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
