import { FaLongArrowAltRight } from "react-icons/fa";

interface MetricCompareProps {
    label: string;
    before: number;
    after: number;
}

const MetricCompare = ({ label, before, after }: MetricCompareProps) => {
    const isBetter = after >= before;

    return (
        <div className="flex flex-col items-center p-3 bg-gray-50 dark:bg-gray-900/50 rounded-xl border border-gray-100 dark:border-gray-800">
            <span className="text-xs font-bold text-gray-500 uppercase">
                {label}
            </span>

            <div className="mt-2 flex items-center gap-3">
                <span className="text-lg font-medium text-gray-400">
                    {(before * 100).toFixed(2)}%
                </span>

                <FaLongArrowAltRight />

                <span
                    className={`text-xl font-bold ${isBetter
                            ? "text-[#4361EE] dark:text-indigo-300"
                            : "text-red-500"
                        }`}
                >
                    {(after * 100).toFixed(2)}%
                </span>
            </div>
        </div>
    );
};

export default MetricCompare;