"use client";
import { isLocalEnvironment } from "@/lib/env";
import { useState, Suspense, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { FiBarChart2, FiCpu } from "react-icons/fi";
import EDATab from "@/components/tabs/edaTab";
import FeatureSelectionTab from "@/components/tabs/featureSelectionTab";
import { useAuth } from "@/context/authcontext";
import { useTranslations } from "next-intl";

function DashboardContent() {
    const t = useTranslations("analyzeDashboard");
    const searchParams = useSearchParams();
    const router = useRouter();

    const datasetId = searchParams.get("id");
    const targetColumn = searchParams.get("target");

    const imputation = searchParams.get("imputation") || "auto";
    const balancing = searchParams.get("balancing") || "no";
    
    const size = searchParams.get("size") ? Number(searchParams.get("size")) : 80;
    const mutationRate = searchParams.get("mutation_rate") ? Number(searchParams.get("mutation_rate")) : 0.2;
    const testSize = searchParams.get("test_size") ? Number(searchParams.get("test_size")) : 0.3;
    const nParentsStr = searchParams.get("n_parents");
    const nParents = nParentsStr ? Number(nParentsStr) : undefined;
    const modelParam = searchParams.get("model");
    const isLocal = isLocalEnvironment();
    const model = (modelParam && (modelParam !== "random_forest" || isLocal)) ? modelParam : "decision_tree";


    const [activeTab, setActiveTab] = useState<"eda" | "fs">("eda");
    const [processedId, setProcessedId] = useState<string | null>(null);
    const { user, loading } = useAuth();

    useEffect(() => {
        if (!loading && !user) {
            router.push("/login");
        }
    }, [user, loading, router]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full min-h-[50vh]">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                <span className="ml-3 text-gray-500 font-medium">{t("verifying")}</span>
            </div>
        );
    }

    if (!user) {
        return null; 
    }

    if (!datasetId || !targetColumn) {
        return (
            <div className="flex flex-col items-center justify-center h-full min-h-[50vh]">
                <p className="text-gray-500">{t("missingInfo")}</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            <div className="=z-40 pt-4 pb-0">
                {/* Phần Tiêu đề */}
                <div className="flex items-center gap-4 mb-4 px-4">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t("title")}</h1>
                        <p className="text-gray-500 dark:text-gray-400 mt-1">
                            {t("targetFeature")} <span className="font-bold text-[#4361EE] uppercase bg-[#4361EE]/10 px-2 py-0.5 rounded ml-1">{targetColumn}</span>
                        </p>
                    </div>
                </div>

                {/* Phần Tab Điều hướng */}
                <div className="flex border-b border-gray-200 dark:border-gray-700 px-4">
                    <button
                        onClick={() => setActiveTab("eda")}
                        className={`flex items-center cursor-pointer p-2 gap-2 mr-2 font-medium transition-all border-b-2 ${activeTab === "eda"
                                ? "border-[#4361EE] text-[#4361EE]"
                                : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                            }`}
                    >
                        <FiBarChart2 className="text-lg" />
                        {t("tabs.eda")}
                    </button>
                    <button
                        onClick={() => setActiveTab("fs")}
                        disabled={!processedId}
                        className={`flex items-center cursor-pointer px-2 gap-2 font-medium transition-all border-b-2 ${!processedId ? "opacity-50 cursor-not-allowed text-gray-400" :
                                activeTab === "fs"
                                    ? "border-[#4361EE] text-[#4361EE]"
                                    : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                            }`}
                    >
                        <FiCpu className="text-lg" />
                        {t("tabs.featureSelection")}
                    </button>
                </div>
            </div>

            {/* VÙNG CHỨA NỘI DUNG CỦA TAB */}
            <div className="px-4 relative">
                <div className={`${activeTab === "eda" ? "block" : "hidden"}`}>
                    <EDATab
                        datasetId={datasetId}
                        targetColumn={targetColumn}
                        imputation={imputation}
                        onProcessed={(id) => setProcessedId(id)}
                        />
                </div>

                <div className={`${activeTab === "fs" ? "block" : "hidden"}`}>
                    <FeatureSelectionTab
                        targetColumn={targetColumn}
                        processedId={processedId}
                        size={size}
                        mutationRate={mutationRate}
                        testSize={testSize}
                        nParents={nParents}
                        balancing={balancing}
                        modelName={model}
                    />
                </div>

            </div>
        </div>
    );
}

export default function AnalysisDashboard() {
    return (
        <Suspense fallback={
            <div className="flex items-center justify-center h-full min-h-[50vh]">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        }>
            <DashboardContent />
        </Suspense>
    );
}
