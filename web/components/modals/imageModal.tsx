"use client";
import { useEffect } from "react";
import Image from "next/image";
import { FiX, FiDownload } from "react-icons/fi";
import { useTranslations } from "next-intl";

interface ImageModalProps {
    imageUrl: string | null;
    onClose: () => void;
}

export default function ImageModal({ imageUrl, onClose }: ImageModalProps) {
    const t = useTranslations("imageModal");
    useEffect(() => {
        if (imageUrl) {
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "unset";
        }

        return () => {
            document.body.style.overflow = "unset";
        };
    }, [imageUrl]);

    // Close modal on Escape key
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape" && imageUrl) {
                onClose();
            }
        };
        if (imageUrl) {
            document.addEventListener("keydown", handleKeyDown);
        }
        return () => {
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [imageUrl, onClose]);

    // Handle image download
    const handleDownload = async () => {
        if (!imageUrl) return;

        try {
            const response = await fetch(imageUrl);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);

            const link = document.createElement("a");
            link.href = url;

            // Extract a filename from the URL or use a default
            const filename = imageUrl.split("/").pop() || "downloaded-image.png";
            link.download = filename;

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error("Failed to download image:", error);
        }
    };

    if (!imageUrl) return null;

    return (
        <div className="relative z-50" aria-labelledby="modal-image" role="dialog">
            <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center p-4">

                {/* Action Buttons Container */}
                <div className="absolute top-6 right-6 flex items-center gap-4 z-50">
                    <button
                        className="hover:cursor-pointer text-gray-300 hover:text-white bg-gray-900/50 hover:bg-gray-900 p-2 rounded-full transition-colors"
                        onClick={handleDownload}
                        title={t("download")}
                        aria-label={t("download")}
                    >
                        <FiDownload className="w-8 h-8" />
                    </button>

                    <button
                        className="hover:cursor-pointer text-gray-300 hover:text-white bg-gray-900/50 hover:bg-gray-900 p-2 rounded-full transition-colors"
                        onClick={onClose}
                        title={t("close")}
                        aria-label={t("close")}
                    >
                        <FiX className="w-8 h-8" />
                    </button>
                </div>

                <div className="relative w-full max-w-6xl h-[85vh]">
                    <Image
                        src={imageUrl}
                        alt={t("alt")}
                        fill
                        sizes="100vw"
                        className="object-contain"
                        priority
                    />
                </div>
            </div>
        </div>
    );
}