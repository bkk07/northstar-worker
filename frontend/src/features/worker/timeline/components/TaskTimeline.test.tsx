import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TaskTimelineView } from "@/features/worker/timeline/components/TaskTimeline";
import type { AuditEventRead } from "@/features/worker/types";

function event(overrides: Partial<AuditEventRead> & { id: string }): AuditEventRead {
  return {
    task_id: "t",
    run_id: "r",
    seq: 1,
    ts: "2026-10-05T00:00:00.000Z",
    node: null,
    tool: null,
    kind: "node.transition",
    status: null,
    error_type: null,
    retry_count: 0,
    duration_ms: null,
    policy_result: null,
    verification_result: null,
    payload: {},
    ...overrides,
  };
}

function renderView(events: AuditEventRead[]) {
  render(
    <TaskTimelineView
      events={events}
      screenshots={[]}
      kindFilter="all"
      onFilter={vi.fn()}
      liveStatus="open"
    />,
  );
}

describe("TaskTimelineView", () => {
  it("badges the failure with its type", () => {
    renderView([
      event({
        id: "a",
        seq: 1,
        node: "classify",
        kind: "failure.classified",
        error_type: "network_error",
      }),
    ]);
    expect(screen.getByRole("status")).toHaveTextContent("FAILURE: network_error");
  });

  it("badges recovery rounds with the strategy", () => {
    renderView([
      event({ id: "a", seq: 2, node: "recover", kind: "recovery.decided", status: "retry_same" }),
      event({
        id: "b",
        seq: 3,
        node: "probe_reconcile",
        kind: "recovery.probe",
        status: "adopted",
      }),
    ]);
    const badges = screen.getAllByRole("status");
    expect(badges[0]).toHaveTextContent("RECOVERY: retry_same");
    expect(badges[1]).toHaveTextContent("RECOVERY: adopted");
  });

  it("highlights decision nodes and policy outcomes", () => {
    renderView([
      event({
        id: "a",
        seq: 4,
        node: "policy_check",
        kind: "policy.decision",
        policy_result: "block",
      }),
      event({
        id: "b",
        seq: 5,
        node: "verify",
        kind: "verification.result",
        verification_result: "verified",
      }),
    ]);
    expect(screen.getByText("policy_check")).toBeInTheDocument();
    expect(screen.getByText("block")).toBeInTheDocument();
    expect(screen.getByText("verified")).toBeInTheDocument();
  });

  it("renders the empty state before the run starts", () => {
    renderView([]);
    expect(screen.getByText(/No events yet/)).toBeInTheDocument();
    expect(screen.getByText(/No screenshots captured/)).toBeInTheDocument();
  });

  it("lists the screenshot gallery paths", () => {
    render(
      <TaskTimelineView
        events={[]}
        screenshots={[
          { run_id: "r", label: "after-submit", path: "shots/after.png", created_at: "" },
        ]}
        kindFilter="all"
        onFilter={vi.fn()}
        liveStatus="open"
      />,
    );
    expect(screen.getByText("after-submit: shots/after.png")).toBeInTheDocument();
  });
});
