"use client";

import { AnimusRouteError } from "@/components/animus/RouteStates";

export default function InterviewError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  return <AnimusRouteError section="interview" title="The interview could not continue" error={error} retry={unstable_retry} />;
}
