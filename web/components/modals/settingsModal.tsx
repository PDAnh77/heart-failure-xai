"use client";
import SettingRow from "@/components/settings/settingRow";
import { useSettings } from "@/context/settingscontext";
import { useTheme } from "next-themes";
import { IoMdClose } from "react-icons/io";
import { useEffect, useState } from "react";
import CustomSelect from "@/components/ui/customSelect";
import { useTranslations } from "next-intl";

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
    const [isVisible, setIsVisible] = useState(false);

    const {
        savePrediction,
        setSavePrediction,
        snowMode,
        setSnowMode,
        language,
        setLanguage,
        isReady,
    } = useSettings();
    const { theme, setTheme } = useTheme();
    const isDarkMode = theme === "dark";
    const t = useTranslations("settings");

    // Xử lý hiệu ứng transition khi mở modal
    useEffect(() => {
        if (isOpen) {
            const timer = setTimeout(() => setIsVisible(true), 10);
            return () => clearTimeout(timer);
        } else {
            setIsVisible(false);
        }
    }, [isOpen]);

    // Ngăn chặn cuộn nền khi modal đang mở
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "unset";
        }
        return () => {
            document.body.style.overflow = "unset";
        };
    }, [isOpen]);

    // Đóng modal khi nhấn phím Escape
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                onClose();
            }
        };
        if (isOpen) {
            document.addEventListener("keydown", handleKeyDown);
        }
        return () => {
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const languageOptions: { value: "vi" | "en"; label: string }[] = [
        { value: "vi", label: t("languageVi") },
        { value: "en", label: t("languageEn") },
    ];

    return (
        <div className="relative z-50" aria-labelledby="modal-title" role="dialog">
            {/* Backdrop */}
            <div
                className={`fixed inset-0 bg-gray-500/75 transition-opacity duration-300 ease-out ${isVisible ? "opacity-100" : "opacity-0"
                    }`}
                onClick={onClose}
            >
                {/* Flex wrapper để canh giữa modal */}
                <div className="flex min-h-full items-center justify-center p-4 text-center sm:p-0">

                    {/* Modal Panel — bỏ overflow-hidden để dropdown không bị clip */}
                    <div
                        className={`relative transform rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 w-full sm:max-w-lg duration-300 ease-out ${isVisible
                                ? "opacity-100 translate-y-0 sm:scale-100"
                                : "opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
                            }`}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-6 dark:bg-gray-800 rounded-lg">

                            {/* Header & Nút đóng */}
                            <div className="flex items-center justify-between mb-5">
                                <h3
                                    className="text-xl font-semibold leading-6 text-gray-900 dark:text-white"
                                    id="modal-title"
                                >
                                    {t("title")}
                                </h3>
                                <button
                                    onClick={onClose}
                                    className="p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-700 dark:text-gray-300 dark:hover:text-gray-50 rounded-full transition-colors hover:cursor-pointer"
                                    aria-label={t("closeAria")}
                                >
                                    <IoMdClose className="w-6 h-6" />
                                </button>
                            </div>

                            {/* Danh sách Settings */}
                            <div className="divide-y divide-gray-200 dark:divide-gray-700">

                                {/* Dark Mode */}
                                <SettingRow
                                    title={t("darkMode")}
                                    description=""
                                    enabled={isDarkMode}
                                    setEnabled={(value) => setTheme(value ? "dark" : "light")}
                                />

                                {/* Language — Custom Select */}
                                <div className="flex items-center justify-between py-4">
                                    <div className="flex flex-col pr-4">
                                        <span className="text-base font-medium text-gray-900 dark:text-white">
                                            {t("language")}
                                        </span>
                                    </div>

                                    <div className="w-40 shrink-0">
                                        <CustomSelect
                                            id="language-select"
                                            value={language}
                                            disabled={!isReady}
                                            onChange={(val) => setLanguage(val as "vi" | "en")}
                                            options={languageOptions}
                                        />
                                    </div>
                                </div>

                                {/* Snow Mode */}
                                <SettingRow
                                    title={t("snowfall")}
                                    description=""
                                    enabled={snowMode}
                                    setEnabled={setSnowMode}
                                />

                                {/* Save Prediction History */}
                                <SettingRow
                                    title={t("savePredictionHistory")}
                                    description=""
                                    enabled={savePrediction}
                                    setEnabled={setSavePrediction}
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}