import { createRoot } from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { lazy, StrictMode, Suspense, useEffect, useState } from "react";
import DashboardPage from "./pages/Dashboard/page";
import MainLayout from "./components/MainLayout";

import "./index.css";
import { I18nextProvider, useTranslation } from "react-i18next";
import i18n from "../i18n/config";
import { pagesList } from "./constants/pagesList";

const NotFoundPage = lazy(() => import("./ui/NotFoundPage"));

const router = createHashRouter([
  {
    Component: MainLayout,
    errorElement: <NotFoundPage />,
    children: [
      { index: true, Component: DashboardPage },
      ...pagesList.map((item) => ({
        index: false,
        Component: item.component,
        path: item.route,
      })),
    ],
  },
]);

const App = () => {
  const { i18n: i18nInstance } = useTranslation();
  const [langLoaded, setLangLoaded] = useState(false);

  // Handle initial language load
  useEffect(() => {
    // Get language from main via IPC (preload needed for electronAPI)
    window.electronAPI.getLanguage().then((lang: string) => {
      i18nInstance.changeLanguage(lang);
      // Set direction for RTL
      document.dir = lang === "fa" || lang === "ar" ? "rtl" : "ltr";

      const body = document.body;
      body.classList.toggle("font-fa", lang === "fa");
      body.classList.toggle("font-ar", lang === "ar");
      body.classList.toggle("font-en", lang === "en");
      setLangLoaded(true);
    });
  }, [i18nInstance]);

  if (!langLoaded) return <div>Loading...</div>; // Or spinner
  return (
    <Suspense fallback="Loading...">
      <RouterProvider router={router} />
    </Suspense>
  );
};

const RootApp = () => (
  <StrictMode>
    <I18nextProvider i18n={i18n}>
      <App />
    </I18nextProvider>
  </StrictMode>
);

const container = document.getElementById("root");
const root = createRoot(container);
root.render(<RootApp />);
