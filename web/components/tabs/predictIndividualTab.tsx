"use client"
import { useRouter } from "next/navigation";
import { FormEvent, useState, useRef } from "react";
import { PredictionResult } from "@/types/prediction";
import { Patient } from "@/types/patient"
import { useSettings } from "@/context/settingscontext";
import { useAuth } from "@/context/authcontext";
import { api } from "@/lib/api";
import toast from "react-hot-toast";
import { FaHeartbeat, FaUserAlt, FaNotesMedical } from "react-icons/fa";
import { useTranslations } from "next-intl";
import CustomSelect, { CustomSelectHandle } from "@/components/ui/customSelect";

export default function PredictIndividualTab() {
    const t = useTranslations("predictIndividual");
    const router = useRouter();
    const [submitting, setSubmitting] = useState(false);
    const [invalidFields, setInvalidFields] = useState<string[]>([]);
    const formRef = useRef<HTMLFormElement>(null);
    const autoFillBtnRef = useRef<HTMLButtonElement>(null);
    const topRef = useRef<HTMLDivElement>(null);

    // Refs để autoFill có thể set value cho các CustomSelect
    const genderRef = useRef<CustomSelectHandle | null>(null);
    const chestPainRef = useRef<CustomSelectHandle | null>(null);
    const fastingBsRef = useRef<CustomSelectHandle | null>(null);
    const restingEcgRef = useRef<CustomSelectHandle | null>(null);
    const stSlopeRef = useRef<CustomSelectHandle | null>(null);
    const { user, loading: authLoading, logout, pushNewHistoryItem } = useAuth();
    const { savePrediction } = useSettings();

    const RequiredMark = () => <span className="text-red-500 font-bold ml-1">*</span>;

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const fieldName = e.target.name;
        if (invalidFields.includes(fieldName)) {
            setInvalidFields(prev => prev.filter(item => item !== fieldName));
        }
    };

    // Dùng cho CustomSelect onChange
    const handleSelectChange = (fieldName: string) => (value: string) => {
        if (value && invalidFields.includes(fieldName)) {
            setInvalidFields(prev => prev.filter(item => item !== fieldName));
        }
    };

    const validateForm = (formData: FormData) => {
        const errors: string[] = [];
        const checkRange = (name: string, min: number, max: number) => {
            const value = formData.get(name);
            if (!value) {
                errors.push(name);
            } else {
                const num = Number(value);
                if (isNaN(num) || num < min || num > max) {
                    errors.push(name);
                }
            }
        };

        const checkRequired = (name: string) => {
            const value = formData.get(name);
            if (!value || value === "") errors.push(name);
        };

        checkRequired("gender");
        checkRange("age", 1, 120);
        checkRequired("chest-pain-type");
        checkRange("resting-bp", 50, 250);
        checkRange("cholesterol", 0, 600);
        checkRequired("fasting-bs");
        checkRequired("resting-ecg");
        checkRange("max-hr", 60, 220);
        checkRequired("exercise-angina");
        checkRange("oldpeak", -5, 10);
        checkRequired("st-slope");

        setInvalidFields(errors);
        return errors.length === 0;
    };

    // Style ô input bo tròn, nền xám như ảnh minh họa
    const getInputClass = (fieldName: string, hasSuffix: boolean = false) => {
        const baseStructure = `block w-full rounded-xl transition h-12 px-4 text-base outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white dark:focus:bg-gray-900 ${hasSuffix ? 'pr-16' : ''}`;
        if (invalidFields.includes(fieldName)) {
            return `${baseStructure} bg-red-50 text-red-800 placeholder:text-red-300 border border-red-500 dark:bg-red-900/20 dark:text-red-200`;
        }
        return `${baseStructure} bg-gray-100 text-gray-900 border border-transparent placeholder:text-gray-400 dark:bg-gray-800 dark:text-white`;
    };

    const handleAutoFillForm = async () => {
        toast.dismiss();
        setInvalidFields([]);
        if (!user) {
            toast.error(t("toast.signInRequired"));
            router.push("/login");
            return;
        }
        if (!formRef.current) return;
        const form = formRef.current;

        try {
            if (autoFillBtnRef.current) {
                autoFillBtnRef.current.innerText = t("buttons.loading");
                autoFillBtnRef.current.disabled = true;
            }

            const res = await api.get("/patients/rand");
            const patient: Patient = res.data;

            if (!patient) return;

            // Hàm set value hỗ trợ radio buttons và CustomSelect refs
            const setValue = (name: string, value: any) => {
                if (name === "exercise-angina") {
                    const radio = form.querySelector(`input[name="exercise-angina"][value="${value}"]`) as HTMLInputElement;
                    if (radio) radio.checked = true;
                    return;
                }
                // CustomSelect: set qua ref
                if (name === "gender") { genderRef.current?.setValue(String(value)); return; }
                if (name === "chest-pain-type") { chestPainRef.current?.setValue(String(value)); return; }
                if (name === "fasting-bs") { fastingBsRef.current?.setValue(String(value)); return; }
                if (name === "resting-ecg") { restingEcgRef.current?.setValue(String(value)); return; }
                if (name === "st-slope") { stSlopeRef.current?.setValue(String(value)); return; }
                // Input thường
                const element = form.querySelector(`[name="${name}"]`) as HTMLInputElement;
                if (element) element.value = String(value);
            }

            setValue('age', patient.age);
            setValue('gender', patient.sex);
            setValue('chest-pain-type', patient.chest_pain_type);
            setValue('resting-bp', patient.resting_bp);
            setValue('cholesterol', patient.cholesterol);
            setValue('fasting-bs', patient.fasting_bs);
            setValue('resting-ecg', patient.resting_ecg);
            setValue('max-hr', patient.max_hr);
            setValue('exercise-angina', patient.exercise_angina);
            setValue('oldpeak', patient.oldpeak);
            setValue('st-slope', patient.st_slope);

        } catch (error: any) {
            if (error.response?.status === 401) {
                logout();
                toast.error(t("toast.sessionExpired"));
                router.push("/login");
                return;
            }
            console.error(error.message);
            toast.error(t("toast.autoFillFailed"));
        } finally {
            if (autoFillBtnRef.current) {
                autoFillBtnRef.current.innerText = t("buttons.autoFillSample");
                autoFillBtnRef.current.disabled = false;
            }
        }
    };

    const handleReset = () => {
        formRef.current?.reset();
        setInvalidFields([]);
        setSubmitting(false);
        toast.dismiss();
        // Reset custom selects về giá trị mặc định
        genderRef.current?.setValue("M");
        chestPainRef.current?.setValue("");
        fastingBsRef.current?.setValue("");
        restingEcgRef.current?.setValue("");
        stSlopeRef.current?.setValue("");

        // Mặc định exercise-angina là No
        const noRadio = formRef.current?.querySelector('input[name="exercise-angina"][value="N"]') as HTMLInputElement;
        if (noRadio) noRadio.checked = true;

        topRef.current?.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
    };

    const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        toast.dismiss();

        if (authLoading) {
            toast.error(t("toast.checkingAuth"));
            return;
        }

        if (!user) {
            toast.error(t("toast.signInRequired"));
            router.push("/login");
            return;
        }

        const formData = new FormData(e.currentTarget);

        if (!validateForm(formData)) {
            topRef.current?.scrollIntoView({ behavior: "smooth" });
            return;
        }

        setSubmitting(true);

        const payload = {
            age: parseInt(formData.get("age") as string),
            sex: formData.get("gender"),
            chest_pain_type: formData.get("chest-pain-type"),
            resting_bp: parseInt(formData.get("resting-bp") as string),
            cholesterol: parseInt(formData.get("cholesterol") as string),
            fasting_bs: parseInt(formData.get("fasting-bs") as string),
            resting_ecg: formData.get("resting-ecg"),
            max_hr: parseInt(formData.get("max-hr") as string),
            exercise_angina: formData.get("exercise-angina"),
            oldpeak: parseFloat(formData.get("oldpeak") as string),
            st_slope: formData.get("st-slope"),
            save_prediction: savePrediction
        };

        try {
            const res = await api.post("/predictions", payload);
            const data: PredictionResult = res.data;
            pushNewHistoryItem({
                id: data.prediction_history.id,
                type: "single",
                created_at: data.prediction_history.created_at || new Date().toISOString()
            });
            router.push(`/prediction-history/${data.prediction_history.id}`)
        } catch (error: any) {
            if (error.response?.status === 401) {
                toast.error(t("toast.sessionExpired"));
                logout();
                router.push("/login");
                return;
            }
            console.error(error);
            toast.error(t("toast.predictionFailed"));
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="p-4 mx-auto">
            <h1 ref={topRef} className="text-2xl font-bold text-gray-900 dark:text-white">{t("title")}</h1>
            <p className="mt-1 text-gray-600 dark:text-gray-400 mb-6">{t("description")}</p>
            <form ref={formRef} onSubmit={handleSubmit} noValidate>
                <div className="bg-white dark:bg-gray-800/60 p-6 md:p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
                    
                    {/* Header: Demographic Title & Auto-fill sample button in top right corner */}
                    <div className="flex items-center justify-between pb-4 mb-6 border-b border-gray-200 dark:border-gray-700">
                        <h3 className="text-lg md:text-xl font-bold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                            <FaUserAlt className="text-indigo-600 dark:text-indigo-400" /> {t("sections.demographic")}
                        </h3>
                        <button
                            type="button"
                            onClick={handleAutoFillForm}
                            ref={autoFillBtnRef}
                            className="rounded-lg px-4 py-2 bg-gray-100 border border-gray-200 text-sm font-semibold text-gray-700 hover:bg-gray-200 cursor-pointer transition-colors dark:bg-gray-700 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-600 shadow-2xs"
                        >
                            {t("buttons.autoFillSample")}
                        </button>
                    </div>

                    {/* Section 1 Inputs: Demographic */}
                    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 mb-8">
                        {/* Gender */}
                        <div>
                            <label htmlFor="gender" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">{t("fields.gender.label")} <RequiredMark /></label>
                            <CustomSelect
                                id="gender"
                                name="gender"
                                defaultValue="M"
                                options={[
                                    { value: "M", label: t("fields.gender.male") },
                                    { value: "F", label: t("fields.gender.female") },
                                ]}
                                isInvalid={invalidFields.includes("gender")}
                                onChange={handleSelectChange("gender")}
                                selectRef={genderRef}
                            />
                            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("fields.gender.description")}</p>
                        </div>
                        {/* Age */}
                        <div>
                            <label htmlFor="age" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">{t("fields.age.label")} <RequiredMark /></label>
                            <input id="age" type="number" name="age" placeholder={t("fields.age.placeholder")} onChange={handleInputChange} className={getInputClass("age")} />
                            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("fields.age.description")}</p>
                        </div>
                    </div>

                    {/* Section 2: Cardiovascular Metrics */}
                    <div className="pt-2 mb-8">
                        <h3 className="text-lg md:text-xl font-bold text-gray-800 dark:text-gray-200 flex items-center gap-2 mb-6 pb-4 border-b border-gray-200 dark:border-gray-700">
                            <FaHeartbeat className="text-indigo-600 dark:text-indigo-400" /> {t("sections.cardiovascular")}
                        </h3>
                        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                            {/* Resting BP */}
                            <div>
                                <label htmlFor="resting-bp" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">{t("fields.restingBp.label")} <RequiredMark /></label>
                                <div className="relative">
                                    <input id="resting-bp" type="number" name="resting-bp" placeholder={t("fields.restingBp.placeholder")} onChange={handleInputChange} className={getInputClass("resting-bp", true)} />
                                    <div className="absolute inset-y-0 right-0 flex items-center pr-4 pointer-events-none">
                                        <span className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">MMHG</span>
                                    </div>
                                </div>
                                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("fields.restingBp.description")}</p>
                            </div>
                            {/* Cholesterol */}
                            <div>
                                <label htmlFor="cholesterol" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">{t("fields.cholesterol.label")} <RequiredMark /></label>
                                <div className="relative">
                                    <input id="cholesterol" type="number" name="cholesterol" placeholder={t("fields.cholesterol.placeholder")} onChange={handleInputChange} className={getInputClass("cholesterol", true)} />
                                    <div className="absolute inset-y-0 right-0 flex items-center pr-4 pointer-events-none">
                                        <span className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">MG/DL</span>
                                    </div>
                                </div>
                                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("fields.cholesterol.description")}</p>
                            </div>
                            {/* Max HR */}
                            <div>
                                <label htmlFor="max-hr" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">{t("fields.maxHr.label")} <RequiredMark /></label>
                                <div className="relative">
                                    <input id="max-hr" type="number" name="max-hr" placeholder={t("fields.maxHr.placeholder")} onChange={handleInputChange} className={getInputClass("max-hr", true)} />
                                    <div className="absolute inset-y-0 right-0 flex items-center pr-4 pointer-events-none">
                                        <span className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">BPM</span>
                                    </div>
                                </div>
                                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("fields.maxHr.description")}</p>
                            </div>
                        </div>
                    </div>

                    {/* Section 3: Symptoms & Clinical History */}
                    <div className="pt-2">
                        <h3 className="text-lg md:text-xl font-bold text-gray-800 dark:text-gray-200 flex items-center gap-2 mb-6 pb-4 border-b border-gray-200 dark:border-gray-700">
                            <FaNotesMedical className="text-indigo-600 dark:text-indigo-400" /> {t("sections.symptoms")}
                        </h3>
                        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                            {/* Chest Pain Type */}
                            <div>
                                <label htmlFor="chest-pain-type" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">{t("fields.chestPainType.label")} <RequiredMark /></label>
                                <CustomSelect
                                    id="chest-pain-type"
                                    name="chest-pain-type"
                                    placeholder={t("fields.chestPainType.placeholder")}
                                    options={[
                                        { value: "TA", label: t("fields.chestPainType.ta") },
                                        { value: "ATA", label: t("fields.chestPainType.ata") },
                                        { value: "NAP", label: t("fields.chestPainType.nap") },
                                        { value: "ASY", label: t("fields.chestPainType.asy") },
                                    ]}
                                    isInvalid={invalidFields.includes("chest-pain-type")}
                                    onChange={handleSelectChange("chest-pain-type")}
                                    selectRef={chestPainRef}
                                />
                                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("fields.chestPainType.description")}</p>
                            </div>
                            {/* Fasting BS */}
                            <div>
                                <label htmlFor="fasting-bs" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">{t("fields.fastingBs.label")} <RequiredMark /></label>
                                <CustomSelect
                                    id="fasting-bs"
                                    name="fasting-bs"
                                    placeholder={t("fields.fastingBs.placeholder")}
                                    options={[
                                        { value: "1", label: t("fields.fastingBs.yes") },
                                        { value: "0", label: t("fields.fastingBs.no") },
                                    ]}
                                    isInvalid={invalidFields.includes("fasting-bs")}
                                    onChange={handleSelectChange("fasting-bs")}
                                    selectRef={fastingBsRef}
                                />
                                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("fields.fastingBs.description")}</p>
                            </div>
                            {/* Resting ECG */}
                            <div>
                                <label htmlFor="resting-ecg" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">{t("fields.restingEcg.label")} <RequiredMark /></label>
                                <CustomSelect
                                    id="resting-ecg"
                                    name="resting-ecg"
                                    placeholder={t("fields.restingEcg.placeholder")}
                                    options={[
                                        { value: "Normal", label: t("fields.restingEcg.normal") },
                                        { value: "ST", label: t("fields.restingEcg.st") },
                                        { value: "LVH", label: t("fields.restingEcg.lvh") },
                                    ]}
                                    isInvalid={invalidFields.includes("resting-ecg")}
                                    onChange={handleSelectChange("resting-ecg")}
                                    selectRef={restingEcgRef}
                                />
                                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("fields.restingEcg.description")}</p>
                            </div>
                            {/* Exercise Angina */}
                            <div>
                                <label className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-3">{t("fields.exerciseAngina.label")} <RequiredMark /></label>
                                <div className="flex items-center gap-8 h-12">
                                    <label className="flex items-center gap-2 cursor-pointer group">
                                        <input type="radio" name="exercise-angina" value="Y" className="w-4 h-4 text-indigo-600 bg-gray-100 border-gray-300 focus:ring-indigo-500 dark:ring-offset-gray-800 dark:bg-gray-700 dark:border-gray-600" onChange={handleInputChange} />
                                        <span className="text-base font-medium text-gray-700 group-hover:text-indigo-600 dark:text-gray-300">{t("fields.exerciseAngina.yes")}</span>
                                    </label>
                                    <label className="flex items-center gap-2 cursor-pointer group">
                                        <input type="radio" name="exercise-angina" value="N" defaultChecked className="w-4 h-4 text-indigo-600 bg-gray-100 border-gray-300 focus:ring-indigo-500 dark:ring-offset-gray-800 dark:bg-gray-700 dark:border-gray-600" onChange={handleInputChange} />
                                        <span className="text-base font-medium text-gray-700 group-hover:text-indigo-600 dark:text-gray-300">{t("fields.exerciseAngina.no")}</span>
                                    </label>
                                </div>
                                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("fields.exerciseAngina.description")}</p>
                                {invalidFields.includes("exercise-angina") && (
                                    <p className="mt-1 text-sm text-red-500">{t("fields.exerciseAngina.required")}</p>
                                )}
                            </div>
                            {/* Oldpeak */}
                            <div>
                                <label htmlFor="oldpeak" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">{t("fields.oldpeak.label")} <RequiredMark /></label>
                                <input id="oldpeak" type="number" name="oldpeak" step="0.1" min="-5" max="10" placeholder={t("fields.oldpeak.placeholder")} onChange={handleInputChange} className={getInputClass("oldpeak")} />
                                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("fields.oldpeak.description")}</p>
                            </div>
                            {/* ST Slope */}
                            <div>
                                <label htmlFor="st-slope" className="block text-base font-semibold text-gray-800 dark:text-gray-200 mb-2">{t("fields.stSlope.label")} <RequiredMark /></label>
                                <CustomSelect
                                    id="st-slope"
                                    name="st-slope"
                                    placeholder={t("fields.stSlope.placeholder")}
                                    options={[
                                        { value: "Up", label: t("fields.stSlope.up") },
                                        { value: "Flat", label: t("fields.stSlope.flat") },
                                        { value: "Down", label: t("fields.stSlope.down") },
                                    ]}
                                    isInvalid={invalidFields.includes("st-slope")}
                                    onChange={handleSelectChange("st-slope")}
                                    selectRef={stSlopeRef}
                                />
                                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t("fields.stSlope.description")}</p>
                            </div>
                        </div>
                    </div>

                    <div className="mt-10 pt-6 flex items-center justify-end gap-x-4 border-t border-gray-100 dark:border-gray-700/60">
                        <button
                            type="button"
                            onClick={handleReset}
                            disabled={submitting}
                            className="rounded-xl px-8 py-3 text-base font-semibold text-gray-700 bg-white border border-gray-200 cursor-pointer hover:bg-gray-50 hover:text-indigo-600 transition-colors shadow-sm dark:bg-gray-800 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {t("buttons.resetForm")}
                        </button>
                        <button
                            type="submit"
                            disabled={submitting}
                            className="rounded-xl bg-indigo-600 px-8 py-3 text-base font-semibold text-white shadow-sm cursor-pointer hover:bg-indigo-700 focus:ring-4 focus:ring-indigo-500/30 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
                        >
                            {submitting ? t("buttons.analyzing") : t("buttons.predict")}
                        </button>
                    </div>
                    
                </div>
            </form>
        </div>
    )
}