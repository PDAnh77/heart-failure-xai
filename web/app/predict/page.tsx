"use client";
import { useState, Suspense, useEffect } from "react";
import { useSearchParams, useRouter, notFound } from "next/navigation";
import { LuUserSearch, LuUsers } from "react-icons/lu";
import PredictIndividualTab from "@/components/tabs/predictIndividualTab";
import PredictBatchTab from "@/components/tabs/predictBatchTab";
import { useTranslations } from "next-intl";

function PredictContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const typeQuery = searchParams.get("type");
    
    // Strict URL enforcement: if type is not exactly 'individual' or 'batch', throw a 404
    if (typeQuery !== "individual" && typeQuery !== "batch") {
        notFound();
    }

    const [activeTab, setActiveTab] = useState<"individual" | "batch">(
        typeQuery
    );
    const t = useTranslations("sidebar");

    const handleTabChange = (tab: "individual" | "batch") => {
        setActiveTab(tab);
        router.push(`/predict?type=${tab}`);
    };

    return (
        <div className="flex flex-col h-full">
            <div className="z-40 pt-4 pb-0">
                {/* Tab Navigation */}
                <div className="flex border-b border-gray-200 dark:border-gray-700 px-4">
                    <button
                        onClick={() => handleTabChange("individual")}
                        className={`flex items-center cursor-pointer p-2 gap-2 mr-2 font-medium transition-all border-b-2 ${activeTab === "individual"
                                ? "border-[#4361EE] text-[#4361EE]"
                                : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                            }`}
                    >
                        <LuUserSearch className="text-lg" />
                        {t("predict")}
                    </button>
                    <button
                        onClick={() => handleTabChange("batch")}
                        className={`flex items-center cursor-pointer p-2 gap-2 mr-2 font-medium transition-all border-b-2 ${activeTab === "batch"
                                ? "border-[#4361EE] text-[#4361EE]"
                                : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                            }`}
                    >
                        <LuUsers className="text-lg" />
                        {t("predictBatch")}
                    </button>
                </div>
            </div>

            {/* TAB CONTENT */}
            <div className="relative flex-1">
                <div className={`${activeTab === "individual" ? "block" : "hidden"} h-full`}>
                    <PredictIndividualTab />
                </div>
                <div className={`${activeTab === "batch" ? "block" : "hidden"} h-full`}>
                    <PredictBatchTab />
                </div>
            </div>
        </div>
    );
}

export default function PredictPage() {
    return (
        <Suspense fallback={
            <div className="flex items-center justify-center h-full min-h-[50vh]">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        }>
            <PredictContent />
        </Suspense>
    );
}
