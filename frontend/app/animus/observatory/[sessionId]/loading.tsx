import { AnimusRouteSkeleton } from "@/components/animus/RouteStates";

export default function Loading() {
  return <AnimusRouteSkeleton section="observatory" label="Loading the local contrast atlas…" />;
}
