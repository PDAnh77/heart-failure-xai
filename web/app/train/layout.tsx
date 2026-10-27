import type { Metadata } from "next";

export const metadata: Metadata = {
    title: {
        absolute: "Train Custom Model"
    },
    description: "Upload your preprocessed dataset and select a machine learning algorithm to train a custom model.",
};

export default function TrainLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return children;
}
