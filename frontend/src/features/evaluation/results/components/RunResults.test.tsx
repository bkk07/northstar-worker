import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RunResultsView } from "@/features/evaluation/results/components/RunResults";
import {
  RunComparisonView,
  deltaCell,
} from "@/features/evaluation/comparison/components/RunComparison";

const DETAIL = {
  run: {
    id: "r1",
    suite: "seeded",
    scenario_count: 2,
    metrics: {
      task_success_rate: 1.0,
      unsafe_action_rate: 0.0,
      avg_tool_calls: 7.5,
      injection_success_rate: null,
    },
    report_md: "",
    created_at: "2026-10-05T00:00:00.000Z",
  },
  results: [
    {
      id: "s1",
      scenario_id: "S5",
      expected_outcome: "BLOCK",
      actual_outcome: "BLOCK",
      outcome_ok: true,
      scores: {},
      created_at: "",
    },
    {
      id: "s2",
      scenario_id: "S4",
      expected_outcome: "CLARIFY",
      actual_outcome: "CLARIFY",
      outcome_ok: true,
      scores: {},
      created_at: "",
    },
  ],
};

describe("RunResultsView", () => {
  it("renders the §26 table with formatted values and targets", () => {
    render(<RunResultsView detail={DETAIL} />);
    expect(screen.getByText("task_success_rate")).toBeInTheDocument();
    expect(screen.getByText("100.0%")).toBeInTheDocument();
    expect(screen.getByText("0.0%")).toBeInTheDocument();
    expect(screen.getByText("7.5")).toBeInTheDocument();
    expect(screen.getAllByText("n/a").length).toBeGreaterThan(0);
    expect(screen.getAllByText("≥ 90%").length).toBeGreaterThan(0);
  });

  it("lists per-scenario pass rows with the outcome pair", () => {
    render(<RunResultsView detail={DETAIL} />);
    expect(screen.getByText("S5")).toBeInTheDocument();
    expect(screen.getByText("expected BLOCK, got BLOCK")).toBeInTheDocument();
    expect(screen.getAllByLabelText("pass")).toHaveLength(2);
  });
});

describe("deltaCell", () => {
  it("signs deltas and admits missing data", () => {
    expect(deltaCell(0.5, 0.75)).toBe("+0.250");
    expect(deltaCell(0.75, 0.5)).toBe("-0.250");
    expect(deltaCell(null, 0.5)).toBe("n/a");
    expect(deltaCell(0.5, undefined)).toBe("n/a");
  });
});

describe("RunComparisonView", () => {
  it("shows baseline, candidate, and delta columns", () => {
    render(
      <RunComparisonView left={{ task_success_rate: 0.5 }} right={{ task_success_rate: 1.0 }} />,
    );
    expect(screen.getByText("+0.500")).toBeInTheDocument();
  });
});
