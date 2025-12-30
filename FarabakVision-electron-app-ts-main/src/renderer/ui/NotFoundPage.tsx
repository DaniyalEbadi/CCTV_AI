import React from "react";
import { useTranslation } from "react-i18next";
import TitleBar from "../components/TitleBar";

const NotFoundPage: React.FC = () => {
  const { t } = useTranslation("notFound");

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <TitleBar />
      <div className="flex flex-col items-center justify-center h-screen bg-neutral-800 text-center p-4">
        <h1 className="text-6xl font-black text-red-500">404</h1>
        <p className="text-2xl mt-4 text-neutral-100">{t("notFound.title")}</p>
        <p className="text-lg mt-2 text-neutral-400">{t("notFound.message")}</p>
        <a
          href="#/"
          className="mt-6 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-all"
        >
          {t("notFound.backToHome")}
        </a>
      </div>
    </div>
  );
};

export default NotFoundPage;
