import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { VersionSummary } from "@/lib/animusStudioApi";
import VersionTimecode from "../VersionTimecode";

function version(number: number, overrides: Partial<VersionSummary> = {}): VersionSummary {
  return {
    version_id: `version-${number}`,
    number,
    branch_id: "main",
    parent_version_id: number > 1 ? `version-${number - 1}` : null,
    source: "refine",
    label: `Version ${number}`,
    intention: null,
    claim_level: "L1_BEHAVIORAL_ASSISTED",
    created_at: "2026-10-24T00:00:00Z",
    content_hash: `hash-${number}`,
    entity_count: number,
    ...overrides,
  };
}

describe("VersionTimecode", () => {
  it("renders nothing for a single-version scene", () => {
    const { container } = render(
      <VersionTimecode
        versions={[version(1)]}
        activeVersionId="version-1"
        previewVersionId={null}
        busy={false}
        onPreview={() => {}}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("marks the head and the version being previewed", () => {
    render(
      <VersionTimecode
        versions={[version(1), version(2), version(3)]}
        activeVersionId="version-3"
        previewVersionId="version-2"
        busy={false}
        onPreview={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: "Preview version 3: Version 3" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByRole("button", { name: "Preview version 2: Version 2" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByText("head")).toBeInTheDocument();
  });

  it("previews the chosen version and disables the strip while loading", () => {
    const onPreview = vi.fn();
    const { rerender } = render(
      <VersionTimecode
        versions={[version(1), version(2)]}
        activeVersionId="version-2"
        previewVersionId={null}
        busy={false}
        onPreview={onPreview}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Preview version 1: Version 1" }));
    expect(onPreview).toHaveBeenCalledWith("version-1");

    rerender(
      <VersionTimecode
        versions={[version(1), version(2)]}
        activeVersionId="version-2"
        previewVersionId={null}
        busy
        onPreview={onPreview}
      />,
    );
    expect(screen.getByRole("button", { name: "Preview version 1: Version 1" })).toBeDisabled();
  });
});
