import { Suspense } from "react";
import { LoginForm } from "./login-form";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginSkeleton />}>
      <LoginForm />
    </Suspense>
  );
}

function LoginSkeleton() {
  return (
    <div className="mx-auto max-w-md px-4 py-16 sm:px-6">
      <div className="h-72 animate-pulse rounded-2xl bg-white shadow-card" />
    </div>
  );
}
