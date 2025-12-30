import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import resourcesToBackend from "i18next-resources-to-backend";

i18n
  .use(
    resourcesToBackend(
      (language: string, namespace: string) =>
        import(`./locales/${language}/${namespace}.json`)
    )
  ) // Lazy-load via dynamic import
  .use(initReactI18next) // Bind to React
  .use(LanguageDetector) // Detect in browser (fallback)
  .init({
    fallbackLng: "en", // Default if no match
    ns: ["common"], // Default namespace (loaded initially if needed)
    defaultNS: "common",
    interpolation: { escapeValue: false }, // React handles escaping
    detection: { order: ["localStorage", "navigator"] }, // Check storage first
  });

export default i18n;
