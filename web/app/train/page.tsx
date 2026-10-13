"use client";
import { useState, ChangeEvent, DragEvent } from "react";
import { useAuth } from "@/context/authcontext";
import { FaUpload, FaDownload, FaBullseye, FaChartBar, FaArrowsRotate, FaMedal, FaShieldHalved } from "react-icons/fa6";
import { FiFileText, FiRefreshCcw } from "react-icons/fi";
import { IoMdClose } from "react-icons/io";
import toast from "react-hot-toast";
import { api } from "@/lib/api";
import CustomSelect from "@/components/ui/customSelect";
import { useTranslations } from "next-intl";

export default function TrainModel() {
    const t = useTranslations("trainModel");

    const [file, setFile] = useState<File | null>(null);
    const [datasetId, setDatasetId] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    // Form states
    const [columns, setColumns] = useState<string[]>([]);
    const [isLoadingColumns, setIsLoadingColumns] = useState(false);
    const [targetColumn, setTargetColumn] = useState("");
    const [modelName, setModelName] = useState("random_forest");

    const modelDisplayNames: Record<string, string> = {
        "svc": "SVC (Support Vector Classification)",
        "logistic_regression": "Logistic Regression",
        "random_forest": "Random Forest",
        "decision_tree": "Decision Tree",
        "knn": "K-Nearest Neighbors",
        "xgboost": "XGBoost",
        "lightgbm": "LightGBM"
    };

    // Action states
    const [isTraining, setIsTraining] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [isDownloading, setIsDownloading] = useState(false);

    const { user } = useAuth();

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        validateAndSetFile(selectedFile);
    };

    const handleDrop = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);
        const droppedFile = e.dataTransfer.files[0];
        validateAndSetFile(droppedFile);
    };

    const validateAndSetFile = (selectedFile: File | undefined) => {
        if (selectedFile) {
            if (!selectedFile.name.endsWith('.csv') && !selectedFile.name.endsWith('.xlsx') && !selectedFile.name.endsWith('.xls')) {
                toast.error(t("toast.invalidFile"));
                return;
            }

            const MAX_SIZE_MB = 10;
            const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

            if (selectedFile.size > MAX_SIZE_BYTES) {
                toast.error(t("toast.fileTooLarge"));
                return;
            }

            setFile(selectedFile);
            setResult(null);
            fetchColumns(selectedFile);
        }
    };

    const fetchColumns = async (uploadedFile: File) => {
        setIsLoadingColumns(true);
        const formData = new FormData();
        formData.append("file", uploadedFile);

        try {
            const response = await api.post("/datasets/upload", formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });
            setDatasetId(response.data.dataset_id);
            setColumns(response.data.columns || []);
            if (response.data.columns && response.data.columns.length > 0) {
                setTargetColumn("");
            }
        } catch (error) {
            console.error("Failed to upload dataset:", error);
            toast.error("Failed to upload dataset.");
        } finally {
            setIsLoadingColumns(false);
        }
    };

    const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const removeFile = () => {
        setFile(null);
        setDatasetId(null);
        setResult(null);
        setColumns([]);
        setTargetColumn("");
    };

    const handleTrain = async () => {
        if (!datasetId) return;

        if (!targetColumn.trim()) {
            toast.error(t("toast.targetRequired"));
            return;
        }

        setIsTraining(true);

        try {
            const response = await api.post(`/train?dataset_id=${datasetId}&model_name=${modelName}&target_column=${targetColumn}`);

            setResult(response.data);
            toast.success(t("toast.trainSuccess"));
        } catch (error: any) {
            const detail = error.response?.data?.detail;
            toast.error(detail ? detail : t("toast.trainError"));
        } finally {
            setIsTraining(false);
        }
    };

    const handleDownloadModel = async () => {
        if (!result?.model_id) return;

        setIsDownloading(true);
        try {
            const response = await api.get(`/train/${result.model_id}/download`, {
                responseType: 'blob'
            });

            // Create a blob URL and trigger download
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `${result.model_id}.pkl`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error: any) {
            toast.error("Failed to download model.");
        } finally {
            setIsDownloading(false);
        }
    };

    const inputClass = "w-full p-3 mt-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition-shadow";

    return (
        <div className="p-4 h-full flex flex-col">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t("title")}</h1>
                <p className="mt-1 text-gray-600 dark:text-gray-400">
                    {t("subtitle")}
                </p>
            </div>

            <div className={`flex flex-col ${!result ? "justify-center" : "justify-start"} align-middle items-center flex-1 my-10 w-full`}>
                <div className="w-full max-w-2xl">

                    {/* Dropzone Area */}
                    {!result && (
                        <>
                            <div
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                                className={`relative border-2 border-dashed rounded-xl p-10 transition-all duration-200 flex flex-col items-center justify-center my-auto
                                    ${isDragging
                                        ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20"
                                        : "border-gray-300 bg-gray-50 dark:border-gray-500 dark:bg-gray-800/50 hover:border-gray-400 dark:hover:border-gray-500"
                                    }`}
                            >
                                {!file ? (
                                    <>
                                        <div className="bg-indigo-100 dark:bg-indigo-900/50 p-4 rounded-full mb-4">
                                            <FaUpload className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
                                        </div>
                                        <p className="text-lg font-medium text-gray-700 dark:text-gray-300 text-center">
                                            {t("dropzone.dragDrop")}
                                        </p>
                                        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 text-center">
                                            {t("dropzone.clickUpload")}
                                        </p>
                                        <input
                                            type="file"
                                            accept=".csv,.xlsx,.xls"
                                            onChange={handleFileChange}
                                            disabled={isTraining}
                                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
                                        />
                                        <span className="px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-semibold shadow-sm pointer-events-none">
                                            {t("dropzone.chooseFile")}
                                        </span>
                                    </>
                                ) : (
                                    <div className="w-full flex items-center justify-between bg-white dark:bg-gray-800 p-4 rounded-lg border border-green-200 dark:border-green-900/50 shadow-sm">
                                        <div className="flex items-center space-x-4">
                                            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                                                <FiFileText className="w-6 h-6 text-green-600 dark:text-green-400" />
                                            </div>
                                            <div className="overflow-hidden">
                                                <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                                                    {file.name}
                                                </p>
                                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                                    {(file.size / 1024 / 1024).toFixed(2)} MB
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center space-x-2">
                                            <button
                                                onClick={removeFile}
                                                disabled={isTraining}
                                                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors hover:cursor-pointer disabled:opacity-50"
                                            >
                                                <IoMdClose className="w-5 h-5 text-red-500" />
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Configurations */}
                            {file && (
                                <div className="mt-6 mb-10 p-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl">
                                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                                        {t("configuration.title")}
                                    </h3>

                                    <div className="mb-6">
                                        <label htmlFor="target-column" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">
                                            {t("configuration.targetColumn.label")} <span className="text-red-500">*</span>
                                        </label>
                                        <CustomSelect
                                            id="target-column"
                                            value={targetColumn}
                                            placeholder={isLoadingColumns ? t("configuration.targetColumn.loading") : t("configuration.targetColumn.select")}
                                            disabled={isLoadingColumns}
                                            onChange={setTargetColumn}
                                            options={columns.map((col) => ({ value: col, label: col }))}
                                        />
                                        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("configuration.targetColumn.desc")}</p>
                                    </div>

                                    <div className="mb-6">
                                        <label htmlFor="model-selection" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">
                                            {t("configuration.modelSelection.label")}
                                        </label>
                                        <CustomSelect
                                            id="model-selection"
                                            value={modelName}
                                            onChange={setModelName}
                                            options={Object.entries(modelDisplayNames).map(([val, lbl]) => ({ value: val, label: lbl }))}
                                        />
                                        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("configuration.modelSelection.desc")}</p>
                                    </div>

                                    <button
                                        onClick={handleTrain}
                                        disabled={!targetColumn || isTraining}
                                        className="mt-8 w-full py-3 hover:cursor-pointer flex justify-center items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 dark:disabled:bg-indigo-800 disabled:hover:bg-indigo-400 text-white font-bold rounded-lg transition-colors shadow-lg"
                                    >
                                        {isTraining ? (
                                            <>
                                                <div className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin"></div>
                                                {t("configuration.training")}
                                            </>
                                        ) : (
                                            t("configuration.confirmBtn")
                                        )}
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Result Area */}
                {result && (
                    <div className="mt-8 w-full">
                        <div className="mb-6 flex flex-col gap-1">
                            <h3 className="text-lg text-gray-600 dark:text-gray-400">
                                {t("result.model")}: <span className="font-bold text-gray-900 dark:text-white">{modelDisplayNames[result.model] || result.model}</span>
                            </h3>
                            <p className="text-lg text-gray-600 dark:text-gray-400">
                                {t("result.target")}: <span className="font-bold text-gray-900 dark:text-white">{result.target_column}</span>
                            </p>
                        </div>

                        <div>
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
                                {/* Accuracy */}
                                <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm flex flex-col justify-between">
                                    <div className="w-10 h-10 rounded-full flex items-center justify-center bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 mb-6">
                                        <FaBullseye className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <p className="text-xs font-bold text-gray-500 mb-1 uppercase tracking-wider">{t("result.metrics.accuracy")}</p>
                                        <p className="text-3xl font-bold text-blue-700 dark:text-blue-500">{(result.accuracy * 100).toFixed(2)}%</p>
                                        <div className="w-full h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full mt-4">
                                            <div className="h-full bg-blue-600 rounded-full" style={{ width: `${(result.accuracy * 100)}%` }}></div>
                                        </div>
                                    </div>
                                </div>

                                {/* Precision */}
                                <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm flex flex-col justify-between">
                                    <div className="w-10 h-10 rounded-full flex items-center justify-center bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 mb-6">
                                        <FaChartBar className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <p className="text-xs font-bold text-gray-500 mb-1 uppercase tracking-wider">{t("result.metrics.precision")}</p>
                                        <p className="text-3xl font-bold text-green-600 dark:text-green-500">{(result.precision * 100).toFixed(2)}%</p>
                                        <div className="w-full h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full mt-4">
                                            <div className="h-full bg-green-500 rounded-full" style={{ width: `${(result.precision * 100)}%` }}></div>
                                        </div>
                                    </div>
                                </div>

                                {/* Recall */}
                                <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm flex flex-col justify-between">
                                    <div className="w-10 h-10 rounded-full flex items-center justify-center bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 mb-6">
                                        <FaArrowsRotate className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <p className="text-xs font-bold text-gray-500 mb-1 uppercase tracking-wider">{t("result.metrics.recall")}</p>
                                        <p className="text-3xl font-bold text-purple-700 dark:text-purple-500">{(result.recall * 100).toFixed(2)}%</p>
                                        <div className="w-full h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full mt-4">
                                            <div className="h-full bg-purple-600 rounded-full" style={{ width: `${(result.recall * 100)}%` }}></div>
                                        </div>
                                    </div>
                                </div>

                                {/* F1 Score */}
                                <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm flex flex-col justify-between">
                                    <div className="w-10 h-10 rounded-full flex items-center justify-center bg-orange-50 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 mb-6">
                                        <span className="font-bold text-sm">F1</span>
                                    </div>
                                    <div>
                                        <p className="text-xs font-bold text-gray-500 mb-1 uppercase tracking-wider">{t("result.metrics.f1")}</p>
                                        <p className="text-3xl font-bold text-orange-600 dark:text-orange-500">{(result.f1_score * 100).toFixed(2)}%</p>
                                        <div className="w-full h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full mt-4">
                                            <div className="h-full bg-orange-500 rounded-full" style={{ width: `${(result.f1_score * 100)}%` }}></div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Cross Validation */}
                            <div className="bg-[#f8faff] dark:bg-gray-800/80 p-6 rounded-2xl border border-blue-100 dark:border-gray-700 shadow-sm mb-6">
                                <div className="flex justify-between items-center mb-6">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 rounded-full flex items-center justify-center bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 shrink-0">
                                            <FaShieldHalved className="w-6 h-6" />
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-bold text-gray-900 dark:text-white">{t("result.metrics.cv")}</h3>
                                            <p className="text-sm text-gray-500 dark:text-gray-400">{t("result.metrics.cvDesc")}</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">{(result.cross_validation_score * 100).toFixed(2)}%</p>
                                        <p className="text-sm text-gray-500 dark:text-gray-400">{t("result.metrics.avgScore")}</p>
                                    </div>
                                </div>
                                <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full">
                                    <div className="h-full bg-blue-600 dark:bg-blue-500 rounded-full" style={{ width: `${(result.cross_validation_score * 100)}%` }}></div>
                                </div>
                            </div>

                            {/* Actions */}
                            <div className="flex gap-4 flex-col sm:flex-row mt-8">
                                <button
                                    onClick={handleDownloadModel}
                                    disabled={isDownloading}
                                    className="flex-1 py-4 px-6 flex justify-center items-center gap-2 bg-[#00a651] hover:bg-[#008f45] dark:bg-[#008f45] dark:hover:bg-[#00a651] text-white font-bold rounded-xl transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                                >
                                    {isDownloading ? (
                                        <div className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin"></div>
                                    ) : (
                                        <FaDownload className="w-5 h-5" />
                                    )}
                                    {t("result.downloadModel")}
                                </button>
                                <button
                                    onClick={() => setResult(null)}
                                    className="flex-1 py-4 px-6 flex justify-center items-center gap-2 bg-white hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700 font-bold rounded-xl transition-colors shadow-sm cursor-pointer"
                                >
                                    <FiRefreshCcw className="w-5 h-5" />
                                    {t("result.trainAnother")}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
