"use client";
import { useState, useRef, useEffect } from "react";
import { IoIosArrowDown, IoIosArrowUp } from "react-icons/io";
import { FiCheck } from "react-icons/fi";

export interface SelectOption {
    value: string;
    label: string;
    disabled?: boolean;
}

export interface CustomSelectHandle {
    setValue: (v: string) => void;
}

export interface CustomSelectProps {
    id: string;
    name?: string;
    options: SelectOption[];
    value?: string;
    defaultValue?: string;
    placeholder?: string;
    isInvalid?: boolean;
    disabled?: boolean;
    className?: string;
    onChange?: (value: string) => void;
    selectRef?: React.RefObject<CustomSelectHandle | null>;
}

export default function CustomSelect({
    id,
    name,
    options,
    value,
    defaultValue = "",
    placeholder,
    isInvalid,
    disabled = false,
    className = "",
    onChange,
    selectRef,
}: CustomSelectProps) {
    const [open, setOpen] = useState(false);
    const [internalSelected, setInternalSelected] = useState(defaultValue);
    const [dropUp, setDropUp] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    // Hỗ trợ cả Controlled (qua prop value) và Uncontrolled (qua defaultValue)
    const selected = value !== undefined ? value : internalSelected;

    // Expose setValue để parent có thể set giá trị từ ngoài (autoFill, reset...)
    useEffect(() => {
        if (selectRef) {
            selectRef.current = {
                setValue: (v: string) => {
                    setInternalSelected(v);
                    onChange?.(v);
                },
            };
        }
    }, [selectRef, onChange]);

    // Đóng dropdown khi click ra ngoài
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        if (open) document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, [open]);

    const toggleOpen = () => {
        if (disabled) return;
        if (!open && containerRef.current) {
            const rect = containerRef.current.getBoundingClientRect();
            const spaceBelow = window.innerHeight - rect.bottom;
            setDropUp(spaceBelow < 220);
        }
        setOpen((prev) => !prev);
    };

    const selectedOption = options.find((o) => o.value === selected);
    const selectedLabel = selectedOption?.label;

    const baseClass = `flex items-center justify-between w-full h-12 rounded-xl px-4 text-base outline-none transition select-none ${
        disabled ? "opacity-60 cursor-not-allowed" : "cursor-pointer"
    }`;

    const stateClass = isInvalid
        ? `bg-red-50 text-red-800 border border-red-500 dark:bg-red-900/20 dark:text-red-200`
        : `bg-gray-100 text-gray-900 border border-transparent dark:bg-gray-800 dark:text-white hover:bg-gray-200/70 dark:hover:bg-gray-700/60`;

    return (
        <div className={`relative ${className}`} ref={containerRef}>
            {/* Hidden input để FormData lấy value khi submit */}
            {name && <input type="hidden" name={name} value={selected} />}

            {/* Trigger */}
            <button
                type="button"
                id={id}
                disabled={disabled}
                onClick={toggleOpen}
                className={`${baseClass} ${stateClass} focus:ring-2 focus:ring-indigo-500 focus:bg-white dark:focus:bg-gray-900 shadow-xs`}
                aria-haspopup="listbox"
                aria-expanded={open}
            >
                <span className={`truncate text-left pr-2 ${!selected && placeholder ? "text-gray-400 dark:text-gray-500 font-normal" : "font-medium"}`}>
                    {selectedLabel ?? placeholder ?? ""}
                </span>
                {open
                    ? <IoIosArrowUp className="w-4 h-4 shrink-0 text-gray-500 dark:text-gray-400" />
                    : <IoIosArrowDown className="w-4 h-4 shrink-0 text-gray-500 dark:text-gray-400" />
                }
            </button>

            {/* Dropdown */}
            {open && (
                <ul
                    role="listbox"
                    className={`absolute z-40 w-full rounded-xl bg-white shadow-xl ring-1 ring-black/10 dark:bg-gray-800 dark:ring-gray-700 p-1 overflow-y-auto max-h-60 animate-in fade-in duration-150 ${
                        dropUp ? "bottom-full mb-1.5" : "top-full mt-1.5"
                    }`}
                >
                    {options.map((option) => {
                        const isSelected = selected === option.value;
                        return (
                            <li
                                key={option.value}
                                role="option"
                                aria-selected={isSelected}
                                onClick={() => {
                                    if (option.disabled) return;
                                    setInternalSelected(option.value);
                                    onChange?.(option.value);
                                    setOpen(false);
                                }}
                                className={`flex items-center justify-between rounded-lg px-3 py-2.5 text-sm transition-colors select-none ${
                                    option.disabled
                                        ? "opacity-40 cursor-not-allowed text-gray-400"
                                        : isSelected
                                        ? "bg-indigo-50 text-indigo-600 font-semibold dark:bg-indigo-950/60 dark:text-indigo-300 cursor-pointer"
                                        : "text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700/60 cursor-pointer"
                                }`}
                            >
                                <span className="truncate pr-2">{option.label}</span>
                                {isSelected && (
                                    <FiCheck className="w-4 h-4 shrink-0 text-indigo-600 dark:text-indigo-400" />
                                )}
                            </li>
                        );
                    })}
                </ul>
            )}
        </div>
    );
}