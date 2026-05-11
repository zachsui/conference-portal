import { Suspense } from "react";
import { RegisterForm } from "./register-form";

export const dynamic = "force-dynamic";

export default function RegisterPage() {
  return (
    <Suspense fallback={<RegisterSkeleton />}>
      <RegisterForm />
    </Suspense>
  );
}

function RegisterSkeleton() {
  return (
    <div className="mx-auto max-w-md px-4 py-16 sm:px-6">
      <div className="h-[480px] animate-pulse rounded-2xl bg-white shadow-card" />
    </div>
  );
}
