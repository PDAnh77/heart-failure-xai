"use client";
import { useState, useEffect, useRef, ChangeEvent, DragEvent } from "react";
import { getFeatureSelectionModelOptions, isLocalEnvironment } from "@/lib/env";
import { useAuth } from "@/context/authcontext";
import { useRouter } from "next/navigation";
import { FaUpload } from "react-icons/fa6";
import { FiFileText, FiChevronDown, FiChevronUp } from "react-icons/fi";
import { IoMdClose } from "react-icons/io";
import toast from "react-hot-toast";
import { api } from "@/lib/api";
import CustomSelect from "@/components/ui/customSelect";
import { useTranslations } from "next-intl";

export default function Upload() {
    const t = useTranslations("analyzeUpload");

    // File states
    const [file, setFile] = useState<File | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Upload & Dataset states
    const [isUploading, setIsUploading] = useState(false);
    const [datasetId, setDatasetId] = useState<string | null>(null);
    const [columns, setColumns] = useState<string[]>([]);
    const { user } = useAuth();

    const [selectedTarget, setSelectedTarget] = useState<string>("");
    const [isPreprocessingOpen, setIsPreprocessingOpen] = useState<boolean>(false);
    const [isFeatureSelectionOpen, setIsFeatureSelectionOpen] = useState<boolean>(false);
    const [imputationMethod, setImputationMethod] = useState<string>("default");
    const [dataBalancing, setDataBalancing] = useState<string>("none");

    // Genetic Algorithm parameters
    const [size, setSize] = useState<number>(80);
    const [mutationRate, setMutationRate] = useState<number>(0.2);
    const [nParents, setNParents] = useState<number | "">("");
    const [testSize, setTestSize] = useState<number>(0.3);
    const [modelName, setModelName] = useState<string>("decision_tree");
    const [isLocal, setIsLocal] = useState<boolean>(false);

    useEffect(() => {
        setIsLocal(isLocalEnvironment());
    }, []);

    const router = useRouter();

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
            const isSupported = selectedFile.name.toLowerCase().match(/\.(csv|xlsx|xls)$/);
            if (!isSupported) {
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
            resetDatasetData();
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
        resetDatasetData();
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const resetDatasetData = () => {
        setDatasetId(null);
        setColumns([]);
        setSelectedTarget("");
        setIsPreprocessingOpen(false);
        setIsFeatureSelectionOpen(false);
    };

    // Handle File Upload API
    const handleUpload = async (fileToUpload?: File) => {
        const targetFile = fileToUpload || file;
        if (!targetFile) return;

        if (!user) {
            toast.error(t("toast.signInRequired"));
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

            const { dataset_id, columns } = response.data;
            setDatasetId(dataset_id);
            setColumns(columns);
        } catch (error) {
            console.error("Upload error:", error);
            toast.error(t("toast.uploadError"));
        } finally {
            setIsUploading(false);
        }
    };

    // Handle Next Step / Proceed
    const handleProceed = () => {
        if (!selectedTarget) {
            toast.error(t("toast.targetRequired"));
            return;
        }

        // Validate Genetic Algorithm parameters
        if (size < 10 || size > 200) {
            toast.error(t("toast.invalidSize"));
            return;
        }

        if (mutationRate < 0.01 || mutationRate > 0.5) {
            toast.error(t("toast.invalidMutationRate"));
            return;
        }

        if (testSize < 0.1 || testSize > 0.5) {
            toast.error(t("toast.invalidTestSize"));
            return;
        }

        if (nParents !== "") {
            const parsedParents = Number(nParents);
            if (parsedParents <= 0) {
                toast.error(t("toast.invalidNParentsMin"));
                return;
            }
            if (parsedParents >= size) {
                toast.error(t("toast.invalidNParentsMax"));
                return;
            }
        }

        // Build query parameters to pass to the dashboard
        const queryParams = new URLSearchParams({
            id: datasetId as string,
            target: selectedTarget,
            imputation: imputationMethod,
            balancing: dataBalancing,
            size: size.toString(),
            mutation_rate: mutationRate.toString(),
            test_size: testSize.toString(),
            model: modelName
        });

        if (nParents !== "") queryParams.append("n_parents", nParents.toString());

        router.push(`/analyze/dashboard?${queryParams.toString()}`);
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

            <div className={`flex flex-col ${!datasetId ? "justify-center" : "justify-start"} items-center flex-1 ${!datasetId ? "" : "mt-8 mb-10"} w-full`}>
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
                                    {t("dropzone.clickUpload")}
                                </p>
                                <input
                                    type="file"
                                    accept=".csv,.xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                                    onChange={handleFileChange}
                                    disabled={isUploading}
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
                                        <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate max-w-[200px] sm:max-w-[300px]">
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
                                        onClick={removeFile}
                                        disabled={isUploading}
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

                    {/* Configurations Area */}
                    {datasetId && columns.length > 0 && (
                        <div className="mt-6 mb-10 p-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl">

                            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                                {t("configuration.title")}
                            </h3>

                            {/* --- Target Selection (Always visible) --- */}
                            <div className="mb-6">
                                <label htmlFor="target-column" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">
                                    {t("configuration.targetColumn.label")} <span className="text-red-500">*</span>
                                </label>
                                <CustomSelect
                                    id="target-column"
                                    value={selectedTarget}
                                    placeholder={t("configuration.targetColumn.placeholder")}
                                    onChange={setSelectedTarget}
                                    options={columns.map((col) => ({ value: col, label: col }))}
                                />
                                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("configuration.targetColumn.desc")}</p>
                            </div>

                            {/* --- Preprocessing Settings --- */}
                            <div className="border-t border-gray-100 dark:border-gray-700 pt-4 mt-6">
                                <button
                                    onClick={() => setIsPreprocessingOpen(!isPreprocessingOpen)}
                                    className="flex justify-between items-center w-full group hover:cursor-pointer"
                                >
                                    <h4 className="text-lg font-semibold text-indigo-600 dark:text-indigo-400 group-hover:text-indigo-700 transition-colors">
                                        {t("configuration.preprocessing.title")}
                                    </h4>
                                    <div className="p-1 rounded-md">
                                        {isPreprocessingOpen ?
                                            <FiChevronUp className="w-5 h-5 text-gray-500" /> :
                                            <FiChevronDown className="w-5 h-5 text-gray-500" />
                                        }
                                    </div>
                                </button>

                                {isPreprocessingOpen && (
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6 mb-2 animate-in fade-in duration-300">
                                        <div>
                                            <label htmlFor="imputation" className="block text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">
                                                {t("configuration.preprocessing.imputation.label")}
                                            </label>
                                            <CustomSelect
                                                id="imputation"
                                                value={imputationMethod}
                                                onChange={setImputationMethod}
                                                options={[
                                                    { value: "default", label: t("configuration.preprocessing.imputation.default") },
                                                    { value: "knn", label: t("configuration.preprocessing.imputation.knn") },
                                                    { value: "mice", label: t("configuration.preprocessing.imputation.mice") },
                                                    { value: "mean", label: t("configuration.preprocessing.imputation.mean") },
                                                ]}
                                            />
                                            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{t("configuration.preprocessing.imputation.desc")}</p>
                                        </div>

                                        <div>
                                            <label htmlFor="balancing" className="block text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">
                                                {t("configuration.preprocessing.balancing.label")}
                                            </label>
                                            <CustomSelect
                                                id="balancing"
                                                value={dataBalancing}
                                                onChange={setDataBalancing}
                                                options={[
                                                    { value: "none", label: t("configuration.preprocessing.balancing.none") },
                                                    { value: "adasyn", label: t("configuration.preprocessing.balancing.adasyn") },
                                                    { value: "smote", label: t("configuration.preprocessing.balancing.smote") },
                                                ]}
                                            />
                                            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                                <strong>{t("configuration.preprocessing.balancing.note")}</strong> {t("configuration.preprocessing.balancing.desc")}
                                            </p>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* --- Feature Selection Settings --- */}
                            <div className="border-t border-gray-100 dark:border-gray-700 pt-4 mt-4">
                                <button
                                    onClick={() => setIsFeatureSelectionOpen(!isFeatureSelectionOpen)}
                                    className="flex justify-between items-center w-full group hover:cursor-pointer"
                                >
                                    <h4 className="text-lg font-semibold text-indigo-600 dark:text-indigo-400 group-hover:text-indigo-700 transition-colors">
                                        {t("configuration.featureSelection.title")}
                                    </h4>
                                    <div className="p-1 rounded-md">
                                        {isFeatureSelectionOpen ?
                                            <FiChevronUp className="w-5 h-5 text-gray-500" /> :
                                            <FiChevronDown className="w-5 h-5 text-gray-500" />
                                        }
                                    </div>
                                </button>

                                {isFeatureSelectionOpen && (
                                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-6 mb-2">
                                        <div className="sm:col-span-2 lg:col-span-3">
                                            <label htmlFor="fs-model" className="block text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">
                                                {t("configuration.featureSelection.model.label")}
                                            </label>
                                            <CustomSelect
                                                id="fs-model"
                                                value={modelName}
                                                onChange={setModelName}
                                                options={getFeatureSelectionModelOptions(isLocal)}
                                            />
                                            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{t("configuration.featureSelection.model.desc")}</p>
                                        </div>
                                        <div>
                                            <label htmlFor="size" className="block text-sm font-semibold text-gray-800 dark:text-gray-200">
                                                {t("configuration.featureSelection.size.label")}
                                            </label>
                                            <input type="number" id="size" min={10} max={200} value={size} onChange={(e) => setSize(Number(e.target.value))} className={inputClass} />
                                            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{t("configuration.featureSelection.size.desc")}</p>
                                        </div>
                                        <div>
                                            <label htmlFor="mutation-rate" className="block text-sm font-semibold text-gray-800 dark:text-gray-200">
                                                {t("configuration.featureSelection.mutationRate.label")}
                                            </label>
                                            <input type="number" step="0.01" id="mutation-rate" min={0.01} max={0.5} value={mutationRate} onChange={(e) => setMutationRate(Number(e.target.value))} className={inputClass} />
                                            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{t("configuration.featureSelection.mutationRate.desc")}</p>
                                        </div>
                                        <div>
                                            <label htmlFor="n-parents" className="block text-sm font-semibold text-gray-800 dark:text-gray-200">
                                                {t("configuration.featureSelection.nParents.label")}
                                            </label>
                                            <input type="number" id="n-parents" value={nParents} onChange={(e) => setNParents(e.target.value ? Number(e.target.value) : "")} placeholder={t("configuration.featureSelection.nParents.placeholder")} className={inputClass} />
                                            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{t("configuration.featureSelection.nParents.desc")}</p>
                                        </div>
                                        <div>
                                            <label htmlFor="test-size" className="block text-sm font-semibold text-gray-800 dark:text-gray-200">
                                                {t("configuration.featureSelection.testSize.label")}
                                            </label>
                                            <input type="number" step="0.05" id="test-size" min={0.1} max={0.5} value={testSize} onChange={(e) => setTestSize(Number(e.target.value))} className={inputClass} />
                                            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{t("configuration.featureSelection.testSize.desc")}</p>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <button
                                onClick={handleProceed}
                                disabled={!selectedTarget}
                                className="mt-8 w-full py-3 hover:cursor-pointer bg-green-600 hover:bg-green-700 disabled:bg-gray-400 dark:disabled:bg-gray-700 disabled:hover:bg-gray-400 dark:disabled:hover:bg-gray-700 disabled:pointer-events-none text-white font-bold rounded-lg transition-colors shadow-lg"
                            >
                                {t("configuration.confirmBtn")}
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
