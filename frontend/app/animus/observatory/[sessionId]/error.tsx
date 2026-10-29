"use client";

import { AnimusRouteError } from "@/components/animus/RouteStates";

export default function ObservatoryError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  return <AnimusRouteError section="observatory" title="The observatory could not continue" error={error} retry={unstable_retry} />;
}
