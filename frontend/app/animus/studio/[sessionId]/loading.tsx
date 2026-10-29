import { AnimusRouteSkeleton } from "@/components/animus/RouteStates";

export default function Loading() {
  return <AnimusRouteSkeleton section="studio" label="Opening the local workbench…" workspace />;
}
