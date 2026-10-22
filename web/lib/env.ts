export const isLocalEnvironment = (): boolean => {
    if (typeof window === "undefined") {
        return process.env.NODE_ENV === "development";
    }
    const hostname = window.location.hostname;
    return (
        process.env.NODE_ENV === "development" ||
        hostname === "localhost" ||
        hostname === "127.0.0.1" ||
        hostname.startsWith("192.168.") ||
        hostname.endsWith(".local")
    );
};

export const getFeatureSelectionModelOptions = (isLocal: boolean) => [
    { value: "decision_tree", label: "Decision Tree (Default)" },
    ...(isLocal ? [{ value: "random_forest", label: "Random Forest" }] : []),
    { value: "knn", label: "K-Nearest Neighbors" },
    { value: "logistic_regression", label: "Logistic Regression" },
    { value: "xgboost", label: "XGBoost" },
    { value: "lightgbm", label: "LightGBM" },
    { value: "svc", label: "SVM" },
];
