"use client";
import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import Image from "next/image";
import { FiTrendingUp, FiInfo, FiDownload, FiPlay, FiBarChart2 } from "react-icons/fi";
import { FaStar, FaCheckCircle, FaBalanceScale } from "react-icons/fa";
import { FaFilter } from "react-icons/fa6";
import { IoSettingsSharp } from "react-icons/io5";
import { api } from "@/lib/api";
import toast from "react-hot-toast";
import { EvalResult, FSResult } from "@/types/feature_selection";
import ImageModal from "../modals/imageModal";
import MetricCompare from "../ui/metricCompare";
import CustomSelect from "../ui/customSelect";

interface FeatureSelectionTabProps {
    targetColumn: string;
    processedId: string | null;
    size: number;
    mutationRate: number;
    testSize: number;
    nParents?: number;
    balancing: string;
}

const LOADING_MESSAGES = [
    "Preparing and validating dataset...",
    "Analyzing feature relevance...",
    "Exploring potential feature combinations...",
    "Evaluating model performance across selections...",
    "Finalizing the most impactful feature set..."
];

const formatModelName = (modelKey: string) => {
    const modelMap: Record<string, string> = {
        "svm": "SVM",
        "logistic_regression": "Logistic Regression",
        "random_forest": "Random Forest",
        "decision_tree": "Decision Tree",
        "knn": "K-Nearest Neighbors",
        "xgboost": "XGBoost",
        "lightgbm": "LightGBM"
    };
    return modelMap[modelKey] || modelKey;
};

export default function FeatureSelectionTab({
    targetColumn,
    processedId,
    size,
    mutationRate,
    testSize,
    nParents,
    balancing
}: FeatureSelectionTabProps) {
    const pollInterval = useRef<NodeJS.Timeout | null>(null);
    const evalPollInterval = useRef<NodeJS.Timeout | null>(null);
    // UI States
    const [isLoading, setIsLoading] = useState(true);
    const [loadingMessageIdx, setLoadingMessageIdx] = useState(0);
    const [result, setResult] = useState<FSResult | null>(null);
    const [isDownloading, setIsDownloading] = useState(false);
    const [selectedImage, setSelectedImage] = useState<string | null>(null);
    const hasFetched = useRef(false);

    // Local states for parameter configuration
    const [localSize, setLocalSize] = useState<number>(size);
    const [localMutationRate, setLocalMutationRate] = useState<number>(mutationRate);
    const [localTestSize, setLocalTestSize] = useState<number>(testSize);
    const [localNParents, setLocalNParents] = useState<number | string>(nParents ?? "");

    // --- State evaluation ---
    const [evalResult, setEvalResult] = useState<EvalResult | null>(null);
    const [isEvalLoading, setIsEvalLoading] = useState(false);

    // State for LIME UI
    const [limeRowIndex, setLimeRowIndex] = useState<number>(0);
    const [isLimeLoading, setIsLimeLoading] = useState(false);

    // State for Data Balancing configuration
    const [localBalancing, setLocalBalancing] = useState<string>(
        balancing.toLowerCase() === "yes" ? "adasyn" : (balancing.toLowerCase() || "none")
    );

    useEffect(() => {
        return () => {
            if (pollInterval.current) clearInterval(pollInterval.current);
            if (evalPollInterval.current) clearInterval(evalPollInterval.current);
        };
    }, []);

    // Rotate loading message every 5 seconds
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isLoading) {
            interval = setInterval(() => {
                setLoadingMessageIdx((prev) => (prev + 1) % LOADING_MESSAGES.length);
            }, 5000);
        }
        return () => clearInterval(interval);
    }, [isLoading]);

    const fetchEvaluation = async (fsDatasetId: string) => {
        setIsEvalLoading(true);
        try {
            const startRes = await api.post(`/datasets/${processedId}/feature-selection-evaluation`, null, {
                params: {
                    fs_dataset_id: fsDatasetId,
                    target_column: targetColumn,
                    test_size: localTestSize,
                    balancing_method: localBalancing
                }
            });

            const taskId = startRes.data.task_id;

            // Xóa interval cũ nếu có
            if (evalPollInterval.current) clearInterval(evalPollInterval.current);

            // Kiểm tra trạng thái mỗi 3s
            evalPollInterval.current = setInterval(async () => {
                try {
                    const statusRes = await api.get(`/datasets/feature-selection/status/${taskId}`);
                    const taskStatus = statusRes.data.status;

                    if (taskStatus === "COMPLETED") {
                        clearInterval(evalPollInterval.current!);

                        // Lấy kết quả lưu vào state
                        setEvalResult(statusRes.data.result);
                        setIsEvalLoading(false);

                        // Sinh đồ thị LIME sau khi Evaluation tải xong
                        setLimeRowIndex(0);
                        await fetchLime(fsDatasetId, 0);

                    } else if (taskStatus === "FAILED") {
                        clearInterval(evalPollInterval.current!);
                        toast.error(statusRes.data.error || "Evaluation failed to generate charts.");
                        setIsEvalLoading(false);
                    }

                } catch (err) {
                    clearInterval(evalPollInterval.current!);
                    toast.error("Lost connection to server while evaluating.");
                    setIsEvalLoading(false);
                }
            }, 3000);

        } catch (error) {
            toast.error("Could not start deep evaluation.");
            setIsEvalLoading(false);
        }
    };

    const fetchLime = async (fsDatasetId: string, rowIndex: number) => {
        setIsLimeLoading(true);
        try {
            const res = await api.get(`/datasets/${processedId}/feature-selection-evaluation/lime`, {
                params: {
                    fs_dataset_id: fsDatasetId,
                    target_column: targetColumn,
                    instance_idx: rowIndex,
                    test_size: localTestSize
                }
            });
            setEvalResult(prev => {
                if (!prev) return prev;
                return {
                    ...prev,
                    lime_chart_before_url: res.data.lime_chart_before_url,
                    lime_chart_after_url: res.data.lime_chart_after_url,
                    xai_score_before: res.data.xai_score_before,
                    xai_score_after: res.data.xai_score_after,
                };
            });
        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Failed to generate LIME explanations.");
        } finally {
            setIsLimeLoading(false);
        }
    };

    // Extracted API call function to allow re-running
    const runFS = useCallback(async (isManualRerun: boolean = false) => {
        if (!processedId || !targetColumn) return;

        setIsLoading(true);
        setLoadingMessageIdx(0);

        try {
            const requestParams: Record<string, any> = {
                target_column: targetColumn,
                size: localSize,
                mutation_rate: localMutationRate,
                test_size: localTestSize,
                balancing_method: localBalancing,
            };

            if (localNParents !== "" && localNParents !== undefined) {
                requestParams.n_parents = Number(localNParents);
            }

            const startRes = await api.post(`/datasets/${processedId}/feature-selection`, null, {
                params: requestParams
            });

            const taskId = startRes.data.task_id;

            if (!taskId) {
                throw new Error("No task_id returned from server");
            }

            // Xóa interval cũ nếu có để tránh chạy đè
            if (pollInterval.current) clearInterval(pollInterval.current);

            // KIỂM TRA TRẠNG THÁI MỖI 3 GIÂY
            pollInterval.current = setInterval(async () => {
                try {
                    const statusRes = await api.get(`/datasets/feature-selection/status/${taskId}`);
                    const taskStatus = statusRes.data.status;

                    if (taskStatus === "COMPLETED") {
                        // Dừng kiểm tra status
                        clearInterval(pollInterval.current!);

                        // Lấy kết quả thực sự nằm trong trường "result" trả về
                        const finalResult = statusRes.data.result;
                        setResult(finalResult);

                        setIsLoading(false);

                        if (isManualRerun) {
                            toast.success("Feature selection rerun completed successfully!");
                        } else {
                            toast.success("Feature selection completed successfully!");
                        }

                        // Chạy tiếp bước Evaluate
                        if (finalResult.fs_dataset_id) {
                            fetchEvaluation(finalResult.fs_dataset_id);
                        }
                    } else if (taskStatus === "FAILED") {
                        clearInterval(pollInterval.current!);
                        toast.error(statusRes.data.error || "Feature selection failed.");
                        setIsLoading(false);
                    }
                    // Nếu status là "PROCESSING" hoặc "PENDING", không làm gì cả, interval sẽ tiếp tục chạy sau 3 giây.

                } catch (err) {
                    clearInterval(pollInterval.current!);
                    toast.error("Lost connection to server while checking task status.");
                    setIsLoading(false);
                }
            }, 3000);

        } catch (error) {
            toast.error("Failed to start feature selection.");
            setIsLoading(false);
            setEvalResult(null);
        }
    }, [processedId, targetColumn, localSize, localMutationRate, localTestSize, localNParents, localBalancing]);

    // Initial API call when component mounts
    useEffect(() => {
        if (!hasFetched.current && processedId && targetColumn) {
            hasFetched.current = true;
            runFS(false);
        }
    }, [processedId, targetColumn, runFS]);

    // --- Validation Logic before Rerun ---
    const handleRerun = () => {
        if (localSize < 10 || localSize > 200) {
            toast.error("Population size must be between 10 and 200.");
            return;
        }

        if (localMutationRate < 0.01 || localMutationRate > 0.5) {
            toast.error("Mutation rate must be between 0.01 and 0.5.");
            return;
        }

        if (localTestSize < 0.1 || localTestSize > 0.5) {
            toast.error("Test size must be between 0.1 and 0.5.");
            return;
        }

        if (localNParents !== "") {
            const parsedParents = Number(localNParents);
            if (parsedParents <= 0) {
                toast.error("Number of parents must be greater than 0.");
                return;
            }
            if (parsedParents >= localSize) {
                toast.error("Number of parents must be less than Population size.");
                return;
            }
        }

        runFS(true);
    };

    const handleDownload = async () => {
        if (!result?.fs_dataset_id) {
            toast.error("Dataset ID not available");
            return;
        }

        setIsDownloading(true);
        try {
            const response = await api.get(
                `/datasets/${result.fs_dataset_id}/download`,
                {
                    responseType: 'blob',
                    params: { target_column: targetColumn }
                }
            );

            const blob = new Blob([response.data], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `feature_selected_dataset.csv`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            toast.error("Failed to download dataset");
        } finally {
            setIsDownloading(false);
        }
    };

    const handleGenerateLime = async () => {
        if (!result?.fs_dataset_id || !processedId || !targetColumn) {
            toast.error("Evaluation data not ready.");
            return;
        }
        if (limeRowIndex < 0) {
            toast.error("Row index must be 0 or greater.");
            return;
        }
        await fetchLime(result.fs_dataset_id, limeRowIndex);
    };

    const accuracyDiff = ((result?.best_ga_accuracy || 0) - (result?.baseline_accuracy || 0)) * 100;

    const inputClass = "w-full p-2 mt-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-[#4361EE] outline-none transition-shadow";

    // Extract balancing info returned from backend (shape: { method, before?, after?, skipped? })
    // Use only when the returned `method` matches the current `localBalancing` selection
    const balancingStats = result?.balancing && result.balancing.method === localBalancing ? result.balancing : null;

    const timestamp = useMemo(() => Date.now(), [evalResult]);

    return (
        <div>
            <div className="flex-1 mt-6">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center min-h-[60vh]">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-8 h-8 border-2 border-[#4361EE] border-t-transparent rounded-full animate-spin"></div>
                            <h3 className="text-2xl font-bold text-gray-800 dark:text-gray-200">
                                Running feature selection
                            </h3>
                        </div>

                        <p className="text-[#4361EE] font-medium text-lg animate-pulse transition-all duration-500 text-center px-4">
                            {LOADING_MESSAGES[loadingMessageIdx]}
                        </p>
                    </div>
                ) : (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">

                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                                    Feature selection results (Genetic algorithm)
                                </h2>
                                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1.5 max-w-2xl">
                                    The algorithm has identified the most predictive subset of features. This helps in reducing dimensionality, preventing overfitting, and improving model training efficiency.
                                </p>
                            </div>

                            <button
                                onClick={handleDownload}
                                disabled={isDownloading}
                                className="flex items-center hover:cursor-pointer justify-center shrink-0 min-w-[200px] gap-2 px-5 py-2.5 bg-linear-to-r from-[#4361EE] to-[#3a52d5] text-white font-semibold rounded-xl shadow-md hover:shadow-lg hover:from-[#3a52d5] hover:to-[#2e41b0] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <FiDownload className="text-lg" />
                                {isDownloading ? "Downloading..." : "Download dataset"}
                            </button>
                        </div>

                        {/* Stats Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Card 1: Best Accuracy */}
                            <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:border-[#1A535C] transition-colors relative flex flex-col">
                                <div className="flex justify-between items-start">
                                    <p className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        Best accuracy
                                    </p>
                                    <div className="w-10 h-10 bg-[#1A535C]/10 rounded-full flex items-center justify-center shrink-0">
                                        <FaCheckCircle className="text-xl text-[#1A535C] dark:text-teal-400" />
                                    </div>
                                </div>

                                <div className="mt-2 flex items-baseline gap-1">
                                    <p className="text-5xl font-black text-gray-900 dark:text-white">
                                        {((result?.best_ga_accuracy || 0) * 100).toFixed(2)}
                                    </p>
                                    <span className="text-3xl font-bold text-gray-600 dark:text-gray-400">%</span>
                                </div>

                                <div className="mt-4 flex items-center gap-1.5 text-sm font-bold text-[#1A535C] dark:text-teal-400">
                                    <FiTrendingUp className="text-base" />
                                    <span>
                                        {accuracyDiff > 0 ? '+' : ''}
                                        {accuracyDiff.toFixed(2)}% vs Baseline
                                    </span>
                                </div>
                            </div>

                            {/* Card 2: Feature Count */}
                            <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:border-[#4361EE] transition-colors relative flex flex-col">
                                <div className="flex justify-between items-start">
                                    <p className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        Feature count
                                    </p>
                                    <div className="w-10 h-10 bg-[#4361EE]/10 rounded-full flex items-center justify-center shrink-0">
                                        <FaFilter className="text-xl text-[#4361EE]" />
                                    </div>
                                </div>

                                <div className="mt-2 flex items-baseline gap-2">
                                    <p className="text-5xl font-black text-gray-900 dark:text-white">
                                        {result?.feature_count}
                                    </p>
                                    <span className="text-lg font-medium text-gray-600 dark:text-gray-400">
                                        Selected
                                    </span>
                                </div>

                                <div className="mt-4 flex items-center gap-1.5 text-sm font-medium text-gray-500 dark:text-gray-400">
                                    <FiInfo className="text-base" />
                                    <span>
                                        Reduced from {result?.original_feature_count} initial features
                                    </span>
                                </div>
                            </div>

                        </div>

                        {/* Data Balancing Info */}
                        <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:border-purple-500 transition-colors relative flex flex-col">

                            <div className="flex justify-between items-center mb-2">
                                <p className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                    Data Balancing: <span className="text-black dark:text-white ml-1">{localBalancing === "none" ? "None" : localBalancing}</span>
                                </p>
                                <div className="w-10 h-10 bg-purple-500/10 rounded-full flex items-center justify-center shrink-0">
                                    <FaBalanceScale className="text-xl text-purple-600 dark:text-purple-400" />
                                </div>
                            </div>

                            <div className="flex-1 flex flex-col justify-center">
                                {localBalancing === "none" ? (
                                    <p className="text-gray-500 font-medium">Dataset used as-is. No balancing applied.</p>
                                ) : balancingStats?.skipped ? (
                                    <div className="bg-orange-50 dark:bg-orange-900/10 p-3 rounded-xl border border-orange-100 dark:border-orange-800/30">
                                        <p className="text-sm font-bold text-orange-600 dark:text-orange-400 uppercase mb-1">Skipped</p>
                                        <p className="text-sm text-orange-700 dark:text-orange-300">{balancingStats.skipped}</p>
                                    </div>
                                ) : balancingStats?.before && balancingStats?.after ? (
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded-xl border border-gray-100 dark:border-gray-800">
                                            <p className="font-bold text-gray-500 uppercase mb-2 border-b border-gray-200 dark:border-gray-700 pb-1.5">Original</p>
                                            <div className="space-y-2">
                                                {Object.entries(balancingStats.before).map(([cls, count]) => (
                                                    <div key={cls} className="flex justify-between text-gray-700 dark:text-gray-300">
                                                        <span>Class {cls}:</span>
                                                        <span className="font-mono font-bold">{count as number}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        <div className="bg-purple-50 dark:bg-purple-900/10 p-3 rounded-xl border border-purple-100 dark:border-purple-800/30">
                                            <p className="font-bold text-purple-500 uppercase mb-2 border-b border-purple-200 dark:border-purple-800/30 pb-1.5">Balanced</p>
                                            <div className="space-y-2">
                                                {Object.entries(balancingStats.after).map(([cls, count]) => (
                                                    <div key={cls} className="flex justify-between text-purple-700 dark:text-purple-300">
                                                        <span>Class {cls}:</span>
                                                        <span className="font-mono font-bold">{count as number}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <p className="text-base text-gray-500 font-medium italic">Processing results...</p>
                                )}
                            </div>
                        </div>

                        {/* Feature List */}
                        <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 overflow-hidden shadow-sm mt-2">
                            <div className="py-4 px-6 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 flex items-center gap-2">
                                <FaStar className="text-[#4361EE] text-xl" />
                                <h3 className="font-bold text-gray-800 dark:text-gray-200">
                                    Optimal feature subset
                                </h3>
                            </div>
                            <div className="p-6">
                                <div className="flex flex-wrap gap-3">
                                    {result?.selected_features.map((feat) => (
                                        <span
                                            key={feat}
                                            className="px-4 py-2 bg-indigo-50 dark:bg-indigo-900/20 text-[#4361EE] dark:text-indigo-300 rounded-xl border border-indigo-100 dark:border-indigo-800/30 font-semibold shadow-sm"
                                        >
                                            {feat}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* --- DEEP EVALUATION --- */}
                        <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 overflow-hidden shadow-sm mt-6">
                            <div className="py-4 px-6 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <FiBarChart2 className="text-[#4361EE] text-xl" />
                                    <h3 className="font-bold text-gray-800 dark:text-gray-200">Impact evaluation</h3>
                                </div>
                            </div>

                            <div className="p-6">
                                {isEvalLoading ? (
                                    <div className="h-64 flex items-center justify-center gap-2 bg-gray-50 dark:bg-gray-900/20 rounded-xl border border-dashed border-gray-200 dark:border-gray-700">
                                        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                                        <p className="text-gray-500">Please wait while we evaluate the selected features...</p>
                                    </div>
                                ) : evalResult ? (
                                    <div className="space-y-4">
                                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                                            {/* Cột trái: Metrics (Chiếm 1/3) */}
                                            <div className="flex flex-col gap-4 lg:col-span-1">
                                                {/* Model Evaluated Box */}
                                                <div className="flex flex-col items-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800/30">
                                                    <span className="text-xs font-bold text-blue-500 dark:text-blue-400 uppercase tracking-wider">Model Using</span>
                                                    <span className="mt-2 text-lg font-bold text-gray-800 dark:text-gray-200">
                                                        {formatModelName(evalResult.model_evaluated)}
                                                    </span>
                                                </div>

                                                <MetricCompare
                                                    label="Accuracy"
                                                    before={evalResult.metrics_before.accuracy}
                                                    after={evalResult.metrics_after.accuracy}
                                                />

                                                <MetricCompare
                                                    label="Recall (Sensitivity)"
                                                    before={evalResult.metrics_before.recall}
                                                    after={evalResult.metrics_after.recall}
                                                />

                                                <MetricCompare
                                                    label="Precision"
                                                    before={evalResult.metrics_before.precision}
                                                    after={evalResult.metrics_after.precision}
                                                />

                                                <MetricCompare
                                                    label="F1-Score"
                                                    before={evalResult.metrics_before.f1_score}
                                                    after={evalResult.metrics_after.f1_score}
                                                />
                                            </div>

                                            {/* Cột phải: Confusion Matrix & ROC (Chiếm 2/3) */}
                                            <div className="flex flex-col gap-6 lg:col-span-2">
                                                {/* Confusion Matrix */}
                                                {evalResult.confusion_matrix_chart_url && (
                                                    <div
                                                        className="relative group cursor-pointer rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden bg-white p-2"
                                                        onClick={() => setSelectedImage(`${evalResult.confusion_matrix_chart_url}?t=${timestamp}`)}
                                                    >
                                                        <Image
                                                            src={`${evalResult.confusion_matrix_chart_url}?t=${timestamp}`}
                                                            alt="Confusion Matrix Comparison"
                                                            width={800}
                                                            height={350}
                                                            className="w-full h-auto max-h-[350px] object-contain"
                                                        />
                                                        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/10 transition-opacity">
                                                            <span className="bg-black/70 text-white text-xs px-3 py-1.5 rounded-md font-medium shadow-sm backdrop-blur-sm">Click to expand</span>
                                                        </div>
                                                    </div>
                                                )}

                                                {/* ROC Curve */}
                                                {evalResult.roc_chart_url && (
                                                    <div
                                                        className="relative group cursor-pointer rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden bg-white p-2"
                                                        onClick={() => setSelectedImage(`${evalResult.roc_chart_url}?t=${timestamp}`)}
                                                    >
                                                        <Image
                                                            src={`${evalResult.roc_chart_url}?t=${timestamp}`}
                                                            alt="ROC Curve Comparison"
                                                            width={800}
                                                            height={500}
                                                            className="w-full h-auto max-h-[450px] object-contain"
                                                        />
                                                        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/10 transition-opacity">
                                                            <span className="bg-black/70 text-white text-xs px-3 py-1.5 rounded-md font-medium shadow-sm backdrop-blur-sm">Click to expand</span>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">

                                            {/* SHAP GLOBAL IMPORTANCE SECTION */}
                                            <div className="space-y-6">
                                                <h3 className="font-bold text-gray-800 dark:text-gray-200">Global importance (SHAP)</h3>

                                                {/* 2.1 SHAP Bar Chart */}
                                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                                    <div className="bg-gray-50 dark:bg-gray-900/20 border border-gray-200 dark:border-gray-700 rounded-xl p-4 flex flex-col items-center">
                                                        <span className="font-semibold text-gray-700 dark:text-gray-300 mb-3 uppercase tracking-wide text-sm">Before Feature Selection</span>
                                                        {evalResult.shap_chart_before_url && (
                                                            <div
                                                                className="relative group cursor-pointer w-full rounded-lg overflow-hidden bg-white border border-gray-100 dark:border-gray-600 p-2"
                                                                onClick={() => setSelectedImage(`${evalResult.shap_chart_before_url}?t=${timestamp}`)}
                                                            >
                                                                <Image
                                                                    src={`${evalResult.shap_chart_before_url}?t=${timestamp}`}
                                                                    alt="SHAP Importance Before"
                                                                    width={600}
                                                                    height={400}
                                                                    className="w-full h-auto max-h-[300px] object-contain"
                                                                />
                                                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/10 transition-opacity rounded-lg">
                                                                    <span className="bg-black/70 text-white text-xs px-3 py-1.5 rounded-md font-medium shadow-sm backdrop-blur-sm">Click to expand</span>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>

                                                    <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800/30 rounded-xl p-4 flex flex-col items-center">
                                                        <span className="font-semibold text-blue-700 dark:text-blue-300 mb-3 uppercase tracking-wide text-sm">After Feature Selection</span>
                                                        {evalResult.shap_chart_after_url && (
                                                            <div
                                                                className="relative group cursor-pointer w-full rounded-lg overflow-hidden bg-white border border-blue-100 dark:border-blue-800 p-2"
                                                                onClick={() => setSelectedImage(`${evalResult.shap_chart_after_url}?t=${timestamp}`)}
                                                            >
                                                                <Image
                                                                    src={`${evalResult.shap_chart_after_url}?t=${timestamp}`}
                                                                    alt="SHAP Importance After"
                                                                    width={600}
                                                                    height={400}
                                                                    className="w-full h-auto max-h-[300px] object-contain"
                                                                />
                                                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/10 transition-opacity rounded-lg">
                                                                    <span className="bg-black/70 text-white text-xs px-3 py-1.5 rounded-md font-medium shadow-sm backdrop-blur-sm">Click to expand</span>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* 2.2 SHAP Beeswarm Chart */}
                                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                                    <div className="bg-gray-50 dark:bg-gray-900/20 border border-gray-200 dark:border-gray-700 rounded-xl p-4 flex flex-col items-center">
                                                        <span className="font-semibold text-gray-700 dark:text-gray-300 mb-3 uppercase tracking-wide text-sm">Before Feature Selection</span>
                                                        {evalResult.shap_beeswarm_before_url && (
                                                            <div
                                                                className="relative group cursor-pointer w-full rounded-lg overflow-hidden bg-white border border-gray-100 dark:border-gray-600 p-2"
                                                                onClick={() => setSelectedImage(`${evalResult.shap_beeswarm_before_url}?t=${timestamp}`)}
                                                            >
                                                                <Image
                                                                    src={`${evalResult.shap_beeswarm_before_url}?t=${timestamp}`}
                                                                    alt="SHAP Beeswarm Before"
                                                                    width={600}
                                                                    height={400}
                                                                    className="w-full h-auto max-h-[300px] object-contain"
                                                                />
                                                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/10 transition-opacity rounded-lg">
                                                                    <span className="bg-black/70 text-white text-xs px-3 py-1.5 rounded-md font-medium shadow-sm backdrop-blur-sm">Click to expand</span>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>

                                                    <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800/30 rounded-xl p-4 flex flex-col items-center">
                                                        <span className="font-semibold text-blue-700 dark:text-blue-300 mb-3 uppercase tracking-wide text-sm">After Feature Selection</span>
                                                        {evalResult.shap_beeswarm_after_url && (
                                                            <div
                                                                className="relative group cursor-pointer w-full rounded-lg overflow-hidden bg-white border border-blue-100 dark:border-blue-800 p-2"
                                                                onClick={() => setSelectedImage(`${evalResult.shap_beeswarm_after_url}?t=${timestamp}`)}
                                                            >
                                                                <Image
                                                                    src={`${evalResult.shap_beeswarm_after_url}?t=${timestamp}`}
                                                                    alt="SHAP Beeswarm After"
                                                                    width={600}
                                                                    height={400}
                                                                    className="w-full h-auto max-h-[300px] object-contain"
                                                                />
                                                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/10 transition-opacity rounded-lg">
                                                                    <span className="bg-black/70 text-white text-xs px-3 py-1.5 rounded-md font-medium shadow-sm backdrop-blur-sm">Click to expand</span>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* LIME LOCAL EXPLANATIONS SECTION */}
                                            <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                                    <div>
                                                        <h3 className="font-bold text-gray-800 dark:text-gray-200">Local explanations (LIME)</h3>
                                                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-2xl">
                                                            The <strong>XAI Score (R²)</strong> indicates the reliability of the explanation for the chosen row. A score closer to 1.0 means the explanation is highly trustworthy.
                                                        </p>
                                                    </div>

                                                    {/* LIME Data Input Row */}
                                                    <div className="flex items-center gap-3 bg-gray-50 dark:bg-gray-900/50 p-2.5 rounded-xl border border-gray-200 dark:border-gray-700">
                                                        <label className="text-sm font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">
                                                            Row index:
                                                        </label>
                                                        <input
                                                            type="number"
                                                            min={0}
                                                            value={limeRowIndex}
                                                            onChange={(e) => setLimeRowIndex(Number(e.target.value))}
                                                            className="w-20 p-1.5 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-[#4361EE] outline-none text-center"
                                                        />
                                                        <button
                                                            className="px-4 py-1.5 cursor-pointer flex items-center justify-center min-w-[100px] bg-[#4361EE] text-white text-sm font-semibold rounded-md hover:bg-[#3a52d5] transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                                            onClick={handleGenerateLime}
                                                            disabled={isLimeLoading}
                                                        >
                                                            {isLimeLoading ? (
                                                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                                            ) : (
                                                                "Generate"
                                                            )}
                                                        </button>
                                                    </div>
                                                </div>

                                                {/* 2.3 LIME Local Explanation */}
                                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative">
                                                    {isLimeLoading && (
                                                        <div className="absolute inset-0 z-10 bg-white/60 dark:bg-gray-900/60 backdrop-blur-sm flex flex-row items-center justify-center gap-3 rounded-xl border border-gray-200 dark:border-gray-700">
                                                            <div className="w-6 h-6 border-2 border-[#4361EE] border-t-transparent rounded-full animate-spin"></div>
                                                            <p className="font-semibold text-gray-700 dark:text-gray-300">Generating LIME for row {limeRowIndex}...</p>
                                                        </div>
                                                    )}

                                                    <div className={`bg-gray-50 dark:bg-gray-900/20 border border-gray-200 dark:border-gray-700 rounded-xl p-4 flex flex-col items-center transition-opacity duration-300 ${isLimeLoading ? "opacity-30" : "opacity-100"}`}>
                                                        <span className="font-semibold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide text-sm">Before Feature Selection</span>

                                                        {/* XAI Score Before */}
                                                        {evalResult.xai_score_before !== undefined && evalResult.xai_score_before !== null && (
                                                            <span className="mb-3 px-3 py-1 text-xs font-bold bg-white dark:bg-gray-800 text-[#4361EE] border border-gray-200 dark:border-gray-700 rounded-md shadow-sm">
                                                                XAI Score (R²): {evalResult.xai_score_before.toFixed(4)}
                                                            </span>
                                                        )}

                                                        {evalResult.lime_chart_before_url && (
                                                            <div
                                                                className="relative group cursor-pointer w-full rounded-lg overflow-hidden bg-white border border-gray-100 dark:border-gray-600 p-2"
                                                                onClick={() => setSelectedImage(`${evalResult.lime_chart_before_url}?t=${timestamp}`)}
                                                            >
                                                                <Image
                                                                    src={`${evalResult.lime_chart_before_url}?t=${timestamp}`}
                                                                    alt="LIME Before"
                                                                    width={600}
                                                                    height={400}
                                                                    className="w-full h-auto max-h-[300px] object-contain"
                                                                />
                                                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/10 transition-opacity rounded-lg">
                                                                    <span className="bg-black/70 text-white text-xs px-3 py-1.5 rounded-md font-medium shadow-sm backdrop-blur-sm">Click to expand</span>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>

                                                    <div className={`bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800/30 rounded-xl p-4 flex flex-col items-center transition-opacity duration-300 ${isLimeLoading ? "opacity-30" : "opacity-100"}`}>
                                                        <span className="font-semibold text-blue-700 dark:text-blue-300 mb-2 uppercase tracking-wide text-sm">After Feature Selection</span>

                                                        {/* XAI Score After */}
                                                        {evalResult.xai_score_after !== undefined && evalResult.xai_score_after !== null && (
                                                            <span className="mb-3 px-3 py-1 text-xs font-bold bg-white dark:bg-gray-800 text-[#4361EE] border border-blue-200 dark:border-blue-800/30 rounded-md shadow-sm">
                                                                XAI Score (R²): {evalResult.xai_score_after.toFixed(4)}
                                                            </span>
                                                        )}

                                                        {evalResult.lime_chart_after_url && (
                                                            <div
                                                                className="relative group cursor-pointer w-full rounded-lg overflow-hidden bg-white border border-blue-100 dark:border-blue-800 p-2"
                                                                onClick={() => setSelectedImage(`${evalResult.lime_chart_after_url}?t=${timestamp}`)}
                                                            >
                                                                <Image
                                                                    src={`${evalResult.lime_chart_after_url}?t=${timestamp}`}
                                                                    alt="LIME After"
                                                                    width={600}
                                                                    height={400}
                                                                    className="w-full h-auto max-h-[300px] object-contain"
                                                                />
                                                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/10 transition-opacity rounded-lg">
                                                                    <span className="bg-black/70 text-white text-xs px-3 py-1.5 rounded-md font-medium shadow-sm backdrop-blur-sm">Click to expand</span>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>

                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-center text-gray-500 py-8">Evaluation data is not available.</div>
                                )}
                            </div>
                        </div>

                        {/* --- CONFIGURATION PANEL --- */}
                        <div className="bg-white dark:bg-gray-800 mb-6 mt-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
                            <div className="py-4 px-6 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 flex items-center gap-2">
                                <IoSettingsSharp className="text-[#4361EE] text-xl" />
                                <h3 className="font-bold text-gray-900 dark:text-white">
                                    Algorithm parameters
                                </h3>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6 p-6">

                                {/* Data Balancing Method Dropdown */}
                                <div>
                                    <label className="block text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">
                                        Data balancing
                                    </label>
                                    <CustomSelect
                                        id="data-balancing"
                                        value={localBalancing}
                                        onChange={setLocalBalancing}
                                        options={[
                                            { value: "none", label: "None" },
                                            { value: "adasyn", label: "ADASYN" },
                                            { value: "smote", label: "SMOTE" },
                                        ]}
                                    />
                                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Choose method to handle imbalanced classes.</p>
                                </div>

                                {/* Population Size */}
                                <div>
                                    <label className="block text-sm font-semibold text-gray-800 dark:text-gray-200">
                                        Population size
                                    </label>
                                    <input
                                        type="number"
                                        value={localSize}
                                        min={10} max={200}
                                        onChange={(e) => setLocalSize(Number(e.target.value))}
                                        className={inputClass}
                                    />
                                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Individuals in each generation (10 - 200).</p>
                                </div>

                                {/* Mutation Rate */}
                                <div>
                                    <label className="block text-sm font-semibold text-gray-800 dark:text-gray-200">
                                        Mutation rate
                                    </label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        min={0.01} max={0.5}
                                        value={localMutationRate}
                                        onChange={(e) => setLocalMutationRate(Number(e.target.value))}
                                        className={inputClass}
                                    />
                                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Probability of feature flipping (0.01 - 0.5).</p>
                                </div>

                                {/* Number of Parents */}
                                <div>
                                    <label className="block text-sm font-semibold text-gray-800 dark:text-gray-200">
                                        Number of parents
                                    </label>
                                    <input
                                        type="number"
                                        value={localNParents}
                                        onChange={(e) => setLocalNParents(e.target.value ? Number(e.target.value) : "")}
                                        placeholder="Default"
                                        className={inputClass}
                                    />
                                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Best individuals kept. (Less than Population).</p>
                                </div>

                                {/* Test Size */}
                                <div>
                                    <label className="block text-sm font-semibold text-gray-800 dark:text-gray-200">
                                        Test size
                                    </label>
                                    <input
                                        type="number"
                                        step="0.05"
                                        min={0.1} max={0.5}
                                        value={localTestSize}
                                        onChange={(e) => setLocalTestSize(Number(e.target.value))}
                                        className={inputClass}
                                    />
                                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Proportion of data for evaluation (0.1 - 0.5).</p>
                                </div>
                            </div>

                            {/* Rerun Button */}
                            <div className="flex justify-end py-4 px-6 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/20 rounded-b-2xl">
                                <button
                                    onClick={handleRerun}
                                    className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#4361EE] text-white font-semibold shadow-md cursor-pointer hover:bg-[#3a52d5] hover:shadow-lg focus:ring-4 focus:ring-indigo-500/30 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
                                >
                                    <FiPlay className="text-sm" />
                                    Rerun selection
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <ImageModal
                imageUrl={selectedImage}
                onClose={() => setSelectedImage(null)}
            />
        </div>
    );
}