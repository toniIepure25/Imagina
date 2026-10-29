"use client";

import { AnimusRouteError } from "@/components/animus/RouteStates";

export default function PracticeError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  return <AnimusRouteError section="practice" title="Practice could not continue" error={error} retry={unstable_retry} />;
}
