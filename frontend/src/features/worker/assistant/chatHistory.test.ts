import { beforeEach, describe, expect, it } from "vitest";
import {
  deleteSession,
  loadSessions,
  newSession,
  saveSession,
  titleFor,
} from "./chatHistory";

beforeEach(() => {
  localStorage.clear();
});

describe("chatHistory", () => {
  it("titles sessions from the first user turn", () => {
    expect(titleFor([])).toBe("New conversation");
    expect(
      titleFor([
        { id: "1", from: "bot", text: "Hi", ts: "t" },
        { id: "2", from: "you", text: "solve ticket TCK-102 please", ts: "t" },
      ]),
    ).toBe("solve ticket TCK-102 please");
    expect(titleFor([{ id: "2", from: "you", text: `x`.repeat(60), ts: "t" }])).toBe(
      `${"x".repeat(42)}…`,
    );
  });

  it("round-trips sessions newest-first and deletes cleanly", () => {
    const first = { ...newSession(), title: "one" };
    const second = { ...newSession(), title: "two" };
    saveSession(first);
    saveSession(second);
    expect(loadSessions().map((s) => s.title)).toEqual(["two", "one"]);
    deleteSession(second.id);
    expect(loadSessions().map((s) => s.title)).toEqual(["one"]);
  });

  it("survives corrupt storage without throwing", () => {
    localStorage.setItem("ns-chat-sessions-v1", "not-json{{{");
    expect(loadSessions()).toEqual([]);
  });
});
