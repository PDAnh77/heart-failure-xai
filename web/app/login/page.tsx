"use client"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation";
import { toast } from 'react-hot-toast';
import { useAuth } from "@/context/authcontext";
import { User } from "@/types/user";
import { FcGoogle } from "react-icons/fc";
import CustomSelect from "@/components/ui/customSelect";
import { api } from "@/lib/api";
import { useTranslations } from "next-intl";

export default function Login() {
    const router = useRouter();
    const [mode, setMode] = useState<"signin" | "signup">("signin");
    const [isDev, setIsDev] = useState(false);

    // Sign in form state
    const [loginId, setLoginId] = useState("");
    const [password, setPassword] = useState("");

    // Sign up form state
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [role, setRole] = useState<"user" | "admin">("user");

    const [errors, setErrors] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const t = useTranslations("login");
    const tCommon = useTranslations("common");

    useEffect(() => {
        // Detect local development environment
        const isLocal =
            process.env.NODE_ENV === "development" ||
            (typeof window !== "undefined" &&
                (window.location.hostname === "localhost" ||
                    window.location.hostname === "127.0.0.1" ||
                    window.location.hostname.startsWith("192.168.")));
        setIsDev(isLocal);
    }, []);

    const handleGoogleLogin = () => {
        window.location.href = "/api/auth/google";
    }

    const handleSignIn = async (e: React.FormEvent) => {
        e.preventDefault();
        setErrors({});
        toast.dismiss();
        let hasError = false;
        const newErrors: Record<string, string> = {};

        if (!loginId.trim()) {
            newErrors.loginId = t("errors.loginIdRequired");
            hasError = true;
        }
        if (!password) {
            newErrors.password = t("errors.passwordRequired");
            hasError = true;
        }

        if (hasError) {
            setErrors(newErrors);
            return;
        }
        setLoading(true);

        const payload = {
            login_id: loginId,
            password: password
        };

        try {
            const res = await api.post("/auth/login", payload);
            const current_user: User = res.data;
            login(current_user);
            setLoginId("");
            setPassword("");
            toast.success(t("toast.success"));
            router.push("/");
        } catch (error: any) {
            if (error.response?.status === 401) {
                toast.error(t("toast.invalidCredentials"));
                return;
            }
            toast.error(t("toast.genericError"));
        } finally {
            setLoading(false);
        }
    };

    const handleSignUp = async (e: React.FormEvent) => {
        e.preventDefault();
        setErrors({});
        toast.dismiss();
        let hasError = false;
        const newErrors: Record<string, string> = {};

        if (!username.trim()) {
            newErrors.username = t("errors.usernameRequired");
            hasError = true;
        }
        if (!password) {
            newErrors.password = t("errors.passwordRequired");
            hasError = true;
        }
        if (password !== confirmPassword) {
            newErrors.confirmPassword = t("errors.passwordsDoNotMatch");
            hasError = true;
        }

        if (hasError) {
            setErrors(newErrors);
            return;
        }
        setLoading(true);

        const payload = {
            username: username.trim(),
            password: password,
            email: email.trim() || undefined,
            role: isDev ? role : "user"
        };

        try {
            await api.post("/auth/signup", payload);

            // Tự động đăng nhập sau khi tạo tài khoản thành công
            try {
                const loginRes = await api.post("/auth/login", {
                    login_id: username.trim(),
                    password: password
                });
                login(loginRes.data);
                toast.success(t("toast.signUpSuccess"));
                router.push("/");
            } catch {
                toast.success(t("toast.signUpSuccess"));
                setMode("signin");
                setLoginId(username.trim());
            }
        } catch (error: any) {
            if (error.response?.status === 409) {
                toast.error(t("toast.userAlreadyExists"));
                return;
            }
            toast.error(t("toast.genericError"));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-full flex-col px-6 py-12 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-sm">
                <h2 className="mt-8 text-center text-2xl/9 font-bold tracking-tight text-gray-900 dark:text-white">
                    {mode === "signin" ? t("title") : t("signUpTitle")}
                </h2>
            </div>

            <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-sm">
                {/* Tabs chuyển đổi giữa Sign In và Sign Up */}
                <div className="flex rounded-xl bg-gray-100 p-1 dark:bg-white/5 mb-6">
                    <button
                        type="button"
                        onClick={() => {
                            setMode("signin");
                            setErrors({});
                        }}
                        className={`flex-1 rounded-lg py-2 text-sm font-semibold transition cursor-pointer ${
                            mode === "signin"
                                ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white"
                                : "text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
                        }`}
                    >
                        {t("tabSignIn")}
                    </button>
                    <button
                        type="button"
                        onClick={() => {
                            setMode("signup");
                            setErrors({});
                        }}
                        className={`flex-1 rounded-lg py-2 text-sm font-semibold transition cursor-pointer flex items-center justify-center gap-1.5 ${
                            mode === "signup"
                                ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white"
                                : "text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
                        }`}
                    >
                        <span>{t("tabSignUp")}</span>
                        {isDev && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                                {t("devBadge")}
                            </span>
                        )}
                    </button>
                </div>

                {mode === "signin" ? (
                    /* FORM SIGN IN */
                    <form onSubmit={handleSignIn} method="POST" noValidate className="space-y-5">
                        <div>
                            <label htmlFor="loginId" className="block text-md/6 font-medium text-gray-900 dark:text-gray-100">
                                {t("fields.loginId")}
                            </label>
                            <div className="mt-2">
                                <input
                                    id="loginId"
                                    name="login_id"
                                    type="text"
                                    value={loginId || ""}
                                    onChange={(e) => {
                                        setLoginId(e.target.value);
                                        if (errors.loginId) setErrors((prev) => ({ ...prev, loginId: "" }));
                                    }}
                                    required
                                    placeholder={t("fields.loginIdPlaceholder")}
                                    className={`block w-full rounded-xl shadow-sm transition bg-white px-4 py-2 text-base text-gray-900 outline-1 -outline-offset-1 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 sm:text-base/6 dark:bg-white/5 dark:text-white dark:placeholder:text-gray-500 ${
                                        errors.loginId
                                            ? "outline-red-500 focus:outline-red-500"
                                            : "outline-gray-300 focus:outline-indigo-600 dark:outline-white/10 dark:focus:outline-indigo-500"
                                    }`}
                                />
                                {errors.loginId && (
                                    <p className="mt-1 text-sm text-red-500 animate-in fade-in duration-200">
                                        {errors.loginId}
                                    </p>
                                )}
                            </div>
                        </div>

                        <div>
                            <div className="flex items-center justify-between">
                                <label htmlFor="password" className="block text-md/6 font-medium text-gray-900 dark:text-gray-100">
                                    {t("fields.password")}
                                </label>
                                <div className="text-sm">
                                    <a
                                        href="#"
                                        tabIndex={-1}
                                        className="hidden font-semibold text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
                                    >
                                        {t("other.forgotPassword")}
                                    </a>
                                </div>
                            </div>
                            <div className="mt-2">
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    value={password || ""}
                                    onChange={(e) => {
                                        setPassword(e.target.value);
                                        if (errors.password) setErrors((prev) => ({ ...prev, password: "" }));
                                    }}
                                    required
                                    placeholder={t("fields.passwordPlaceholder")}
                                    autoComplete="current-password"
                                    className={`block w-full rounded-xl shadow-sm transition bg-white px-4 py-2 text-base text-gray-900 outline-1 -outline-offset-1 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 sm:text-base/6 dark:bg-white/5 dark:text-white dark:placeholder:text-gray-500 ${
                                        errors.password
                                            ? "outline-red-500 focus:outline-red-500"
                                            : "outline-gray-300 focus:outline-indigo-600 dark:outline-white/10 dark:focus:outline-indigo-500"
                                    }`}
                                />
                                {errors.password && (
                                    <p className="mt-1 text-sm text-red-500 animate-in fade-in duration-200">
                                        {errors.password}
                                    </p>
                                )}
                            </div>
                        </div>

                        <div>
                            <button
                                type="submit"
                                disabled={loading}
                                className="flex w-full transition justify-center rounded-md bg-indigo-600 px-3 py-2 text-base/6 font-semibold text-white shadow-xs hover:bg-indigo-500 cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:bg-indigo-500 dark:shadow-none dark:hover:bg-indigo-400 dark:focus-visible:outline-indigo-500"
                            >
                                {loading ? t("actions.signingIn") : t("actions.signIn")}
                            </button>
                        </div>
                    </form>
                ) : (
                    /* FORM SIGN UP */
                    <form onSubmit={handleSignUp} method="POST" noValidate className="space-y-4">
                        <div>
                            <label htmlFor="username" className="block text-md/6 font-medium text-gray-900 dark:text-gray-100">
                                {t("fields.username")} <span className="text-red-500">*</span>
                            </label>
                            <div className="mt-1.5">
                                <input
                                    id="username"
                                    name="username"
                                    type="text"
                                    value={username}
                                    onChange={(e) => {
                                        setUsername(e.target.value);
                                        if (errors.username) setErrors((prev) => ({ ...prev, username: "" }));
                                    }}
                                    required
                                    placeholder={t("fields.usernamePlaceholder")}
                                    className={`block w-full rounded-xl shadow-sm transition bg-white px-4 py-2 text-base text-gray-900 outline-1 -outline-offset-1 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 sm:text-base/6 dark:bg-white/5 dark:text-white dark:placeholder:text-gray-500 ${
                                        errors.username
                                            ? "outline-red-500 focus:outline-red-500"
                                            : "outline-gray-300 focus:outline-indigo-600 dark:outline-white/10 dark:focus:outline-indigo-500"
                                    }`}
                                />
                                {errors.username && (
                                    <p className="mt-1 text-sm text-red-500 animate-in fade-in duration-200">
                                        {errors.username}
                                    </p>
                                )}
                            </div>
                        </div>

                        <div>
                            <label htmlFor="email" className="block text-md/6 font-medium text-gray-900 dark:text-gray-100">
                                {t("fields.email")}
                            </label>
                            <div className="mt-1.5">
                                <input
                                    id="email"
                                    name="email"
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder={t("fields.emailPlaceholder")}
                                    className="block w-full rounded-xl shadow-sm transition bg-white px-4 py-2 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-base/6 dark:bg-white/5 dark:text-white dark:outline-white/10 dark:placeholder:text-gray-500 dark:focus:outline-indigo-500"
                                />
                            </div>
                        </div>

                        {/* Tùy chọn vai trò (Role) trong môi trường Local Dev */}
                        {isDev && (
                            <div>
                                <label htmlFor="role" className="block text-md/6 font-medium text-gray-900 dark:text-gray-100 mb-1.5">
                                    {t("fields.role")}
                                </label>
                                <CustomSelect
                                    id="role"
                                    name="role"
                                    value={role}
                                    onChange={(val) => setRole(val as "user" | "admin")}
                                    options={[
                                        { value: "user", label: t("fields.roleUser") },
                                        { value: "admin", label: t("fields.roleAdmin") },
                                    ]}
                                />
                            </div>
                        )}

                        <div>
                            <label htmlFor="signUpPassword" className="block text-md/6 font-medium text-gray-900 dark:text-gray-100">
                                {t("fields.password")} <span className="text-red-500">*</span>
                            </label>
                            <div className="mt-1.5">
                                <input
                                    id="signUpPassword"
                                    name="password"
                                    type="password"
                                    value={password}
                                    onChange={(e) => {
                                        setPassword(e.target.value);
                                        if (errors.password) setErrors((prev) => ({ ...prev, password: "" }));
                                    }}
                                    required
                                    placeholder={t("fields.passwordPlaceholder")}
                                    className={`block w-full rounded-xl shadow-sm transition bg-white px-4 py-2 text-base text-gray-900 outline-1 -outline-offset-1 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 sm:text-base/6 dark:bg-white/5 dark:text-white dark:placeholder:text-gray-500 ${
                                        errors.password
                                            ? "outline-red-500 focus:outline-red-500"
                                            : "outline-gray-300 focus:outline-indigo-600 dark:outline-white/10 dark:focus:outline-indigo-500"
                                    }`}
                                />
                                {errors.password && (
                                    <p className="mt-1 text-sm text-red-500 animate-in fade-in duration-200">
                                        {errors.password}
                                    </p>
                                )}
                            </div>
                        </div>

                        <div>
                            <label htmlFor="confirmPassword" className="block text-md/6 font-medium text-gray-900 dark:text-gray-100">
                                {t("fields.confirmPassword")} <span className="text-red-500">*</span>
                            </label>
                            <div className="mt-1.5">
                                <input
                                    id="confirmPassword"
                                    name="confirm_password"
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => {
                                        setConfirmPassword(e.target.value);
                                        if (errors.confirmPassword) setErrors((prev) => ({ ...prev, confirmPassword: "" }));
                                    }}
                                    required
                                    placeholder={t("fields.confirmPasswordPlaceholder")}
                                    className={`block w-full rounded-xl shadow-sm transition bg-white px-4 py-2 text-base text-gray-900 outline-1 -outline-offset-1 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 sm:text-base/6 dark:bg-white/5 dark:text-white dark:placeholder:text-gray-500 ${
                                        errors.confirmPassword
                                            ? "outline-red-500 focus:outline-red-500"
                                            : "outline-gray-300 focus:outline-indigo-600 dark:outline-white/10 dark:focus:outline-indigo-500"
                                    }`}
                                />
                                {errors.confirmPassword && (
                                    <p className="mt-1 text-sm text-red-500 animate-in fade-in duration-200">
                                        {errors.confirmPassword}
                                    </p>
                                )}
                            </div>
                        </div>

                        <div className="pt-2">
                            <button
                                type="submit"
                                disabled={loading}
                                className="flex w-full transition justify-center rounded-md bg-indigo-600 px-3 py-2 text-base/6 font-semibold text-white shadow-xs hover:bg-indigo-500 cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:bg-indigo-500 dark:shadow-none dark:hover:bg-indigo-400 dark:focus-visible:outline-indigo-500"
                            >
                                {loading ? t("actions.signingUp") : t("actions.signUp")}
                            </button>
                        </div>
                    </form>
                )}

                {/* Phần Social Login (Google) */}
                <div className="mt-6">
                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <span className="w-full border-t border-gray-300 dark:border-gray-600" />
                        </div>
                        <div className="relative flex justify-center text-sm">
                            <span className="bg-white dark:bg-[#0a0a0a] px-2 text-gray-500 dark:text-gray-400">
                                {t("other.orSignInWith")}
                            </span>
                        </div>
                    </div>

                    <div className="mt-6">
                        <button
                            onClick={handleGoogleLogin}
                            type="button"
                            className="flex w-full transition items-center justify-center gap-2 rounded-md bg-white px-3 py-2 border border-gray-200 dark:border-gray-600 text-base/6 font-semibold text-gray-900 shadow-sm hover:bg-gray-50 cursor-pointer dark:bg-white/10 dark:text-white dark:hover:bg-white/20"
                        >
                            <FcGoogle className="text-2xl" />
                            {tCommon("google")}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}