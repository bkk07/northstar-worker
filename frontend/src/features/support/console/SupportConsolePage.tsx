import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAssistant } from "@/features/worker/assistant/useAssistant";
import { eventsToMessages } from "@/features/worker/chat/components/TaskChat";
import { decideApproval } from "@/features/worker/api/workerApi";
import { useTaskTimeline, useWorkerTask } from "@/features/worker/hooks/useWorker";
import type { TicketRead } from "@/features/shop/types";
import { getErrorMessage } from "@/shared/lib/errors";
import { PageHeader } from "@/shared/ui/page-header";
import { ChatPanel } from "./ChatPanel";
import { ContextPanel } from "./ContextPanel";
import { RaiseTicketDialog } from "./RaiseTicketDialog";
import { TicketRail } from "./TicketRail";

const TERMINAL = new Set(["succeeded", "failed", "cancelled"]);

/**
 * Chatbot-first support console: ticket rail, bot thread, context rail.
 * The bot answers anything about tickets/orders/products/policies, runs
 * solves with live narration, and decides only through Approve/Reject
 * buttons bound to approval ids.
 */
export default function SupportConsolePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    messages,
    send,
    appendBot,
    newChat,
    switchSession,
    activeSessionId,
    busy,
    error,
    retry,
    activeTaskId,
  } = useAssistant(searchParams.get("sid"));
  const [selected, setSelected] = useState<string | null>(null);
  const [raiseOpen, setRaiseOpen] = useState(false);
  const deepLinkHandled = useRef(false);
  const queryClient = useQueryClient();

  const timeline = useTaskTimeline(activeTaskId ?? undefined);
  const taskQuery = useWorkerTask(activeTaskId ?? undefined);
  const task = taskQuery.data;
  const taskStatus = task?.status;
  const narration = eventsToMessages(timeline.data ?? []);

  useEffect(() => {
    if (!activeTaskId || !taskStatus || TERMINAL.has(taskStatus)) return;
    const timer = setInterval(() => taskQuery.refetch(), 3000);
    return () => clearInterval(timer);
  }, [activeTaskId, taskStatus, taskQuery]);

  // Sidebar session switches (?sid=) swap the thread without remounting.
  const sid = searchParams.get("sid");
  useEffect(() => {
    if (sid && sid !== activeSessionId) switchSession(sid);
  }, [sid, activeSessionId, switchSession]);

  // Sidebar "New chat" (?new=1) starts a blank thread.
  useEffect(() => {
    if (searchParams.get("new") === "1") {
      newChat();
      setSearchParams(sid ? { sid } : {}, { replace: true });
    }
  }, []);

  // Deep links from chat actions (?solve= / ?product= / ?policies=1).
  useEffect(() => {
    if (deepLinkHandled.current) return;
    deepLinkHandled.current = true;
    const solve = searchParams.get("solve");
    const product = searchParams.get("product");
    const policies = searchParams.get("policies");
    if (solve) {
      setSelected(solve);
      send(`Solve ticket ${solve}`);
    } else if (product) {
      send(`What is the policy for ${product}?`);
    } else if (policies) {
      send("What is the refund policy?");
    } else {
      return;
    }
    setSearchParams(sid ? { sid } : {}, { replace: true });
  }, []);

  const decide = useMutation({
    mutationFn: ({ approvalId, decision }: { approvalId: string; decision: "approve" | "reject" }) =>
      decideApproval(approvalId, decision, "operator"),
    onSuccess: (approval, variables) => {
      appendBot(
        `${variables.decision === "approve" ? "Approved" : "Rejected"} task ${approval.task_id.slice(0, 8)} — the run resumes on its own.`,
      );
      queryClient.invalidateQueries({ queryKey: ["worker", "approvals"] });
      taskQuery.refetch();
    },
    onError: (failure) => {
      appendBot(`That decision didn't land: ${getErrorMessage(failure)}`);
    },
  });

  function askAbout(code: string) {
    setSelected(code);
    send(`Tell me about ${code}`);
  }

  function solve(code: string) {
    setSelected(code);
    send(`Solve ticket ${code}`);
  }

  function created(ticket: TicketRead) {
    setRaiseOpen(false);
    setSelected(ticket.code);
    appendBot(`Ticket ${ticket.code} is raised — handing it to the solver now.`);
    send(`Solve ticket ${ticket.code}`);
  }

  return (
    <div className="ns-page flex flex-col gap-4">
      <PageHeader
        title="Support console"
        desc="Pick a ticket, ask the bot anything, and watch it solve — approvals use the buttons."
      />
      <div className="grid min-h-0 flex-1 gap-4 xl:h-[calc(100vh-230px)] xl:grid-cols-[290px_minmax(0,1fr)_330px]">
        <div className="flex min-h-0 flex-col">
          <TicketRail
            selected={selected}
            onSelect={askAbout}
            onSolve={solve}
            onRaise={() => setRaiseOpen(true)}
          />
        </div>
        <div className="flex min-h-[60vh] min-h-0 flex-col xl:min-h-0">
          <ChatPanel
            messages={messages}
            narration={narration}
            taskStatus={taskStatus}
            activeTaskId={activeTaskId}
            busy={busy || timeline.isLoading}
            error={error}
            deciding={decide.isPending ? (decide.variables?.approvalId ?? null) : null}
            onRetry={retry}
            onSend={send}
            onDecide={(approvalId, decision) => decide.mutate({ approvalId, decision })}
          />
        </div>
        <div className="flex min-h-0 flex-col">
          <ContextPanel
            ticketCode={selected}
            deciding={decide.isPending ? (decide.variables?.approvalId ?? null) : null}
            onAsk={send}
            onSolve={solve}
            onDecide={(approvalId, decision) => decide.mutate({ approvalId, decision })}
          />
        </div>
      </div>
      <RaiseTicketDialog
        open={raiseOpen}
        onClose={() => setRaiseOpen(false)}
        onCreated={created}
      />
    </div>
  );
}
