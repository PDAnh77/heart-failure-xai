"use client";
import { useRouter } from "next/navigation";
import { useState, useRef, DragEvent, ChangeEvent } from "react";
import { useAuth } from "@/context/authcontext";
import { api } from "@/lib/api";
import toast from "react-hot-toast";
import { FaUpload } from "react-icons/fa6";
import { FiFileText, FiInfo } from "react-icons/fi";
import { IoMdClose } from "react-icons/io";
import { useTranslations } from "next-intl";

export default function PredictBatchTab() {
    const router = useRouter();
    const t = useTranslations("predictBatch");
    const tCommon = useTranslations("common");

    // File states
    const [file, setFile] = useState<File | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    // Upload & Predict states
    const [isUploading, setIsUploading] = useState(false);
    const [isPredicting, setIsPredicting] = useState(false);
    const [datasetId, setDatasetId] = useState<string | null>(null);

    const { user, loading: authLoading, logout, pushNewHistoryItem } = useAuth();
    const fileInputRef = useRef<HTMLInputElement>(null);

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
            if (!selectedFile.name.toLowerCase().match(/\.(csv|xlsx|xls)$/)) {
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
            setDatasetId(null);
            handleUpload(selectedFile);
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
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    // Upload file to get dataset_id
    const handleUpload = async (fileToUpload?: File) => {
        const targetFile = fileToUpload || file;
        if (authLoading || !targetFile) return;

        if (!user) {
            toast.error(tCommon("signInRequired"));
            router.push("/login");
            return;
        }

        setIsUploading(true);
        const formData = new FormData();
        formData.append("file", targetFile);

        try {
            const response = await api.post("/datasets/upload", formData, {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
            });

            const { dataset_id, original_file_type } = response.data;
            sessionStorage.setItem("uploadFileType", original_file_type);
            setDatasetId(dataset_id);
        } catch (error: any) {
            if (error.response?.status === 401) {
                toast.error("Session expired. Please sign in again.");
                logout();
                router.push("/login");
                return;
            }
            toast.error(t("toast.uploadError"));
        } finally {
            setIsUploading(false);
        }
    };

    // Run Batch Prediction
    const handlePredict = async () => {
        toast.dismiss();

        if (!file || !datasetId) return;

        setIsPredicting(true);

        try {
            const res = await api.post(`/predictions/upload/${datasetId}`);

            const historyId = res.data.batch_prediction_id;

            pushNewHistoryItem({
                id: historyId,
                type: "batch",
                created_at: res.data.created_at || new Date().toISOString()
            });

            router.push(`/prediction-history/batch/${historyId}`);
        } catch (error: any) {
            if (error.response) {
                const status = error.response.status;
                const detail = error.response.data?.detail;

                if (status === 401) {
                    toast.error("Session expired. Please sign in again.");
                    logout();
                    router.push("/login");
                    return;
                }

                if (status === 400 && detail?.missing_columns) {
                    const missing = detail.missing_columns.join(", ");
                    toast.error(`${t("toast.missingColumns")} ${missing}.`);
                    return;
                }

                if (status === 422) {
                    toast.error(t("toast.invalidData"));
                    return;
                }
            }

            toast.error(t("toast.predictError"));
        } finally {
            setIsPredicting(false);
        }
    };

    return (
        <div className="p-4 h-full flex flex-col">
            <div className="flex justify-between items-start md:items-center flex-col md:flex-row gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t("title")}</h1>
                    <p className="mt-1 text-gray-600 dark:text-gray-400">
                        {t("subtitle")}
                    </p>
                </div>
            </div>

            <div className="flex flex-col justify-start items-center flex-1 mt-8 mb-10 w-full">
                <div className="w-full max-w-2xl">
                    {/* Dropzone Area */}
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
                                    {t("dropzone.formatLimit")}
                                </p>
                                <input
                                    type="file"
                                    accept=".csv,.xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                                    onChange={handleFileChange}
                                    disabled={isUploading || isPredicting}
                                    ref={fileInputRef}
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
                                        <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate max-w-[200px] sm:max-w-[400px]">
                                            {file.name}
                                        </p>
                                        <p className="text-xs text-gray-500 dark:text-gray-400">
                                            {(file.size / 1024 / 1024).toFixed(2)} MB
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-2">
                                    {isUploading && (
                                        <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mr-2"></div>
                                    )}
                                    <button
                                        type="button"
                                        onClick={removeFile}
                                        disabled={isUploading || isPredicting}
                                        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors hover:cursor-pointer disabled:opacity-50"
                                    >
                                        <IoMdClose className="w-5 h-5 text-red-500" />
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Retry Upload Button if failed */}
                    {file && !datasetId && !isUploading && (
                        <button
                            onClick={() => handleUpload(file)}
                            className="mt-6 w-full py-3 flex justify-center items-center gap-2 bg-indigo-600 hover:bg-indigo-700 hover:cursor-pointer text-white font-bold rounded-lg transition-colors shadow-lg"
                        >
                            {t("uploadBtn.upload")}
                        </button>
                    )}

                    {/* Dataset Requirements Info (Show when no file is chosen) */}
                    {!file && (
                        <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-5 shadow-sm mb-10">
                            <div className="flex items-center gap-2 mb-3">
                                <FiInfo className="text-blue-600 dark:text-blue-400 w-5 h-5" />
                                <h3 className="font-semibold text-blue-900 dark:text-blue-300 text-lg">
                                    {t("requirements.title")}
                                </h3>
                            </div>
                            <p className="text-sm text-blue-800 dark:text-blue-200 mb-4">
                                {t("requirements.description")}
                            </p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-sm text-gray-700 dark:text-gray-300">
                                <ul className="space-y-2 list-disc list-inside">
                                    <li>{t("requirements.fields.age")}</li>
                                    <li>{t("requirements.fields.sex")}</li>
                                    <li>{t("requirements.fields.chestPainType")}</li>
                                    <li>{t("requirements.fields.restingBp")}</li>
                                    <li>{t("requirements.fields.cholesterol")}</li>
                                    <li>{t("requirements.fields.fastingBs")}</li>
                                </ul>
                                <ul className="space-y-2 list-disc list-inside">
                                    <li>{t("requirements.fields.restingEcg")}</li>
                                    <li>{t("requirements.fields.maxHr")}</li>
                                    <li>{t("requirements.fields.exerciseAngina")}</li>
                                    <li>{t("requirements.fields.oldpeak")}</li>
                                    <li>{t("requirements.fields.stSlope")}</li>
                                </ul>
                            </div>
                        </div>
                    )}

                    {/* Prediction Action & Notice */}
                    {datasetId && (
                        <div className="mt-6 mb-10 w-full animate-in fade-in duration-300">
                            {/* Notice Info Box */}
                            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-5 mb-6 shadow-xs">
                                <div className="flex items-center gap-2 mb-2">
                                    <FiInfo className="text-amber-600 dark:text-amber-400 w-5 h-5 shrink-0" />
                                    <p className="font-semibold text-amber-900 dark:text-amber-300">
                                        {t("configuration.systemNotice")}
                                    </p>
                                </div>
                                <p className="text-sm text-amber-800 dark:text-amber-200">
                                    {t("configuration.noticeDescription")}
                                </p>
                            </div>

                            {/* Submit Prediction Button */}
                            <button
                                onClick={handlePredict}
                                disabled={isPredicting || isUploading}
                                className="w-full py-3.5 flex justify-center items-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-green-400 dark:disabled:bg-green-800 hover:cursor-pointer text-white font-bold rounded-xl transition-colors shadow-lg disabled:cursor-not-allowed text-base"
                            >
                                {isPredicting ? (
                                    <>
                                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                        {t("predictBtn.processing")}
                                    </>
                                ) : (
                                    t("predictBtn.run")
                                )}
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
