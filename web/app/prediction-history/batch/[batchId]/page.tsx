"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { FiDownload, FiUsers, FiAlertTriangle, FiCheckCircle } from "react-icons/fi";
import { api } from "@/lib/api";
import toast from "react-hot-toast";
import { BatchResult } from "@/types/batch";
import Image from "next/image";
import ImageModal from "@/components/modals/imageModal";
import PatientDetailModal, { PatientRow } from "@/components/modals/patientDetailModal";
import { useTranslations } from "next-intl";

export default function BatchHistoryDetailPage() {
    const params = useParams();
    const router = useRouter();
    const batchId = params.batchId as string;
    const t = useTranslations("predictionBatchHistoryDetail");

    const [resultData, setResultData] = useState<BatchResult | null>(null);
    const [originalFileType, setOriginalFileType] = useState<string>("csv");
    const [isDownloading, setIsDownloading] = useState(false);
    const [createdAt, setCreatedAt] = useState<string | null>(null);

    // States for Infinite Scroll
    const [patients, setPatients] = useState<PatientRow[]>([]);
    const [page, setPage] = useState(0);
    const [loadingMore, setLoadingMore] = useState(false);
    const [hasMore, setHasMore] = useState(true);
    const limit = 12;

    // States for Modals & XAI
    const [modalImageUrl, setModalImageUrl] = useState<string | null>(null);
    const [selectedPatient, setSelectedPatient] = useState<PatientRow | null>(null);
    const [patientXAI, setPatientXAI] = useState<any>(null);
    const [loadingXAI, setLoadingXAI] = useState(false);
    const [isLoadingInitial, setIsLoadingInitial] = useState(true);

    const loadedPagesRef = useRef<Set<number>>(new Set());
    const observer = useRef<IntersectionObserver | null>(null);

    const lastElementRef = useCallback((node: HTMLDivElement) => {
        if (loadingMore) return;
        if (observer.current) observer.current.disconnect();
        observer.current = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting && hasMore) {
                setPage(prev => prev + 1);
            }
        });
        if (node) observer.current.observe(node);
    }, [loadingMore, hasMore]);

    // Fetch Batch History
    useEffect(() => {
        const fetchBatchHistory = async () => {
            if (!batchId) return;

            try {
                setIsLoadingInitial(true);
                const res = await api.get(`/predictions/batch/${batchId}`);
                const data = res.data;

                if (data.created_at) {
                    setCreatedAt(data.created_at);
                }


                const formattedData: BatchResult = {
                    file_id: data.result_dataset_id,
                    summary: data.summary,
                    batch_shap_bar: data.batch_xai.batch_shap_bar,
                    batch_shap_beeswarm: data.batch_xai.batch_shap_beeswarm,
                };

                setResultData(formattedData);

                // Nếu backend có trả về file type gốc, bạn set ở đây, nếu không mặc định csv
                setOriginalFileType("csv");

                // Reset states danh sách
                setPatients([]);
                loadedPagesRef.current = new Set();

                // Bắt đầu fetch trang dữ liệu đầu tiên
                fetchPatients(data.result_dataset_id, 0);
            } catch (error) {
                toast.error(t("toast.notFound"));
            } finally {
                setIsLoadingInitial(false);
            }
        };

        fetchBatchHistory();
    }, [batchId, router]);

    useEffect(() => {
        if (page > 0 && resultData?.file_id) {
            fetchPatients(resultData.file_id, page);
        }
    }, [page, resultData?.file_id]);

    const fetchPatients = async (fileId: string, currentPage: number) => {
        if (loadedPagesRef.current.has(currentPage)) return;
        loadedPagesRef.current.add(currentPage);

        try {
            setLoadingMore(true);
            const offset = currentPage * limit;
            const res = await api.get(`/datasets/${fileId}/rows`, {
                params: { limit, offset }
            });

            const newData: PatientRow[] = res.data.data;

            setPatients(prev => {
                const prevStrings = new Set(prev.map(item => JSON.stringify(item)));
                const uniqueNewData = newData.filter(
                    item => !prevStrings.has(JSON.stringify(item))
                );

                // Chỉ merge những data mới
                const merged = [...prev, ...uniqueNewData];

                if (newData.length < limit || merged.length >= res.data.total_rows) {
                    setHasMore(false);
                }
                return merged;
            });
        } catch (error) {
            loadedPagesRef.current.delete(currentPage);
            toast.error(t("toast.loadPatientsFailed"));
        } finally {
            setLoadingMore(false);
        }
    };

    const handleDownloadProcessed = async () => {
        const processedId = resultData?.file_id;
        if (!processedId) return;

        try {
            setIsDownloading(true);
            const response = await api.get(`/datasets/${processedId}/download`, {
                responseType: 'blob',
                params: { file_type: originalFileType }
            });

            const fileExtension = originalFileType.includes('xls') ? 'xlsx' : 'csv';
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.download = `result.${fileExtension}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            toast.error(t("toast.downloadFailed"));
        } finally {
            setIsDownloading(false);
        }
    };

    const handleViewPatientDetail = async (patient: PatientRow) => {
        setSelectedPatient(patient);
        setPatientXAI(null);

        try {
            setLoadingXAI(true);
            const res = await api.post(`/predictions/xai/on-demand`, patient);
            setPatientXAI(res.data);
        } catch (error) {
            toast.error(t("toast.generateXAIFailed"));
        } finally {
            setLoadingXAI(false);
        }
    };

    if (isLoadingInitial) {
        return (
            <div className="relative min-h-full">
                <div className="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-gray-900/50 backdrop-blur-sm z-10">
                    <div className="py-3 flex justify-center gap-2 items-center">
                        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                        <p className="text-gray-500">{t("state.loading")}</p>
                    </div>
                </div>
            </div>
        );
    }

    if (!resultData) {
        return (
            <div className="relative min-h-full">
                <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-500 bg-white/50 dark:bg-gray-900/50 backdrop-blur-sm z-10">
                    <p>{t("state.notFound")}</p>
                </div>
            </div>
        );
    }

    const { summary, batch_shap_bar, batch_shap_beeswarm, file_id } = resultData;

    const resultKey = "prediction_result";
    const probabilityKey = "prediction_probability";
    const hiddenKeys = new Set([resultKey, probabilityKey]);

    const formatDateTime = (dateString: string | null) => {
        if (!dateString) return "";
        const date = new Date(dateString);
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const year = date.getFullYear();
        return `(${hours}:${minutes} - ${day}/${month}/${year})`;
    };

    return (
        <div className="p-4 min-h-screen flex flex-col">
            {/* Header & Controls */}
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start mb-4 pb-4 gap-4">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                    {t("header.title")} {formatDateTime(createdAt)}
                </h1>
                <button
                    onClick={handleDownloadProcessed}
                    disabled={isDownloading || !file_id}
                    className="flex items-center hover:cursor-pointer justify-center shrink-0 min-w-[200px] gap-2 px-5 py-2.5 bg-indigo-600 text-white font-semibold rounded-xl shadow-md hover:bg-indigo-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    <FiDownload className="text-lg" />
                    {isDownloading ? t("header.downloading") : t("header.downloadData")}
                </button>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                {/* Total Patients */}
                <div className="bg-white dark:bg-gray-800 p-5 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col justify-between relative overflow-hidden">
                    <div className="flex justify-between items-center text-[#8B7E74] dark:text-gray-400">
                        <p className="text-xs font-bold tracking-wider uppercase">{t("summary.totalPatients")}</p>
                        <FiUsers className="w-5 h-5 text-[#8B7E74]/70 dark:text-gray-500" />
                    </div>
                    <p className="text-4xl font-bold text-[#111827] dark:text-white mt-2">{summary.total}</p>
                </div>

                {/* High Risk */}
                <div className="bg-white dark:bg-gray-800 p-5 rounded-xl border border-red-200 dark:border-red-900/50 shadow-sm flex flex-col justify-between relative overflow-hidden">
                    <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#B91C1C] dark:text-red-500"></div>
                    <div className="flex justify-between items-center text-[#8B7E74] dark:text-gray-400 pl-2">
                        <p className="text-xs font-bold tracking-wider uppercase">{t("summary.highRisk")}</p>
                        <FiAlertTriangle className="w-5 h-5 text-[#B91C1C] dark:text-red-500" />
                    </div>
                    <p className="text-4xl font-bold text-[#B91C1C] dark:text-red-500 mt-2 pl-2 flex items-baseline gap-2">
                        {summary.disease}
                        <span className="text-2xl font-bold">({(summary.disease_ratio * 100).toFixed(1)}%)</span>
                    </p>
                </div>

                {/* Low Risk */}
                <div className="bg-white dark:bg-gray-800 p-5 rounded-xl border border-green-200 dark:border-green-900/50 shadow-sm flex flex-col justify-between relative overflow-hidden">
                    <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#047857] dark:text-green-500"></div>
                    <div className="flex justify-between items-center text-[#8B7E74] dark:text-gray-400 pl-2">
                        <p className="text-xs font-bold tracking-wider uppercase">{t("summary.lowRisk")}</p>
                        <FiCheckCircle className="w-5 h-5 text-[#047857] dark:text-green-500" />
                    </div>
                    <p className="text-4xl font-bold text-[#047857] dark:text-green-500 mt-2 pl-2 flex items-baseline gap-2">
                        {summary.normal}
                        <span className="text-2xl font-bold">({(summary.normal_ratio * 100).toFixed(1)}%)</span>
                    </p>
                </div>
            </div>

            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 mt-4">{t("xai.title")}</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-10">

                {/* SHAP Bar Chart */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col">
                    <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-4">{t("xai.shapBarTitle")}</h3>
                    <div
                        className="relative w-full aspect-video bg-gray-50 dark:bg-gray-900 rounded-lg overflow-hidden cursor-pointer hover:opacity-90 transition-opacity"
                        onClick={() => setModalImageUrl(batch_shap_bar)}
                    >
                        <Image src={batch_shap_bar} alt="SHAP Bar Chart" priority fill sizes="(max-width: 1024px) 100vw, 50vw" className="object-contain p-2" />
                        <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 bg-black/10 transition-opacity">
                            <span className="bg-black/50 text-white text-xs px-2 py-1 rounded-md">{t("xai.clickToExpand")}</span>
                        </div>
                    </div>
                    <p className="text-sm text-gray-500 mt-4 text-center dark:text-gray-400">
                        {t("xai.shapBarDesc")}
                    </p>
                </div>

                {/* SHAP Beeswarm Chart */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col">
                    <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-4">{t("xai.shapBeeswarmTitle")}</h3>
                    <div
                        className="relative w-full aspect-video bg-gray-50 dark:bg-gray-900 rounded-lg overflow-hidden cursor-pointer hover:opacity-90 transition-opacity"
                        onClick={() => setModalImageUrl(batch_shap_beeswarm)}
                    >
                        <Image src={batch_shap_beeswarm} alt="SHAP Beeswarm Chart" priority fill sizes="(max-width: 1024px) 100vw, 50vw" className="object-contain p-2" />
                        <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 bg-black/10 transition-opacity">
                            <span className="bg-black/50 text-white text-xs px-2 py-1 rounded-md">{t("xai.clickToExpand")}</span>
                        </div>
                    </div>
                    <p className="text-sm text-gray-500 mt-4 text-center dark:text-gray-400">
                        {t("xai.shapBeeswarmDesc1")}
                        <span className="font-bold text-red-500">{t("xai.shapBeeswarmRed")}</span>
                        {t("xai.shapBeeswarmMiddle")}
                        <span className="font-bold text-blue-500">{t("xai.shapBeeswarmBlue")}</span>
                        {t("xai.shapBeeswarmEnd")}
                    </p>
                </div>
            </div>

            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">{t("patientList.title")}</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-2 gap-4">
                {patients.map((patient, index) => {
                    const resultValue = patient[resultKey] ?? patient.prediction_result;
                    const isHighRisk = Number(resultValue) === 1;
                    const displayAge = patient.Age || patient.age || patient.age_years || t("patientList.na");
                    const displaySex = patient.Sex || patient.sex || patient.gender || t("patientList.na");
                    const prob = patient[probabilityKey] ?? patient.prediction_probability ?? 0;

                    return (
                        <div
                            key={index}
                            ref={index === patients.length - 1 ? lastElementRef : null}
                            onClick={() => handleViewPatientDetail(patient)}
                            className={`p-4 rounded-xl border cursor-pointer transition-all duration-300 hover:shadow-md dark:hover:shadow-lg ${isHighRisk
                                ? "border-red-200 dark:border-red-800 dark:hover:bg-red-950/20"
                                : "border-green-200 dark:border-green-800 dark:hover:bg-green-950/20"
                                }`}
                        >
                            <div className="flex justify-between items-start mb-3">
                                <span className="font-semibold text-gray-700 dark:text-gray-200">
                                    {t("patientList.patientNum")} #{index + 1}
                                </span>
                                <span className={`px-2.5 py-1 text-[10px] font-bold rounded-full uppercase tracking-wider ${isHighRisk ? "bg-red-200 text-red-800" : "bg-green-200 text-green-800"}`}>
                                    {isHighRisk ? t("patientList.highRisk") : t("patientList.normal")}
                                </span>
                            </div>
                            <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1.5">
                                <p className="flex justify-between"><span>{t("patientList.age")}</span> <span className="font-medium text-gray-800 dark:text-gray-300">{displayAge}</span></p>
                                <p className="flex justify-between"><span>{t("patientList.sex")}</span> <span className="font-medium text-gray-800 dark:text-gray-300">{displaySex}</span></p>
                                <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700/50 flex justify-between">
                                    <span>{t("patientList.confidence")}</span>
                                    <span className="font-bold text-gray-900 dark:text-white">{(prob * 100).toFixed(1)}%</span>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {loadingMore && (
                <div className="flex justify-center gap-2 py-4 text-gray-500">
                    <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                    <span>{t("state.loadingMore")}</span>
                </div>
            )}

            <PatientDetailModal
                patient={selectedPatient}
                onClose={() => setSelectedPatient(null)}
                resultKey={resultKey}
                probabilityKey={probabilityKey}
                hiddenKeys={hiddenKeys}
                loadingXAI={loadingXAI}
                patientXAI={patientXAI}
                onImageClick={(url: string) => setModalImageUrl(url)}
            />

            <ImageModal
                imageUrl={modalImageUrl}
                onClose={() => setModalImageUrl(null)}
            />
        </div>
    );
}