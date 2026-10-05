import { ArrowLeft, History, MessagesSquare, PanelRight, UserRound } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { Badge } from "@/shared/ui/badge";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
import { PageEnter, PageEnterItem } from "@/shared/ui/page-header";
import { NoteForm, ReplyForm, StatusControl } from "../../notes/components/NoteForms";
import { RefundForm } from "../../refunds/components/RefundForm";
import { ReplacementForm } from "../../replacements/components/ReplacementForm";
import { TicketQueue } from "../components/TicketQueue";
import { useTicketDetail } from "../hooks/useTickets";

function scrollToForm(cardId: string, focusId: string) {
  const card = document.getElementById(cardId);
  card?.scrollIntoView({ behavior: "smooth", block: "start" });
  window.setTimeout(() => document.getElementById(focusId)?.focus({ preventScroll: true }), 350);
}

export default function TicketDetailPage() {
  const { ticketCode } = useParams();
  const detail = useTicketDetail(ticketCode);
  const refresh = () => detail.refetch();

  if (detail.isPending)
    return (
      <main className="ns-page">
        <LoadingState what="ticket" />
      </main>
    );
  if (detail.isError || !detail.data)
    return (
      <main className="ns-page">
        <ErrorState message={getErrorMessage(detail.error)} />
      </main>
    );
  const ticket = detail.data;

  return (
    <main className="ns-page space-y-5">
      {/* Hero */}
      <div>
        <Link
          to="/ops/tickets"
          className="inline-flex items-center gap-1 text-[13px] font-medium text-slate-500 hover:text-slate-900"
        >
          <ArrowLeft aria-hidden className="h-3.5 w-3.5" />
          Back to queue
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{ticket.code}</h1>
          <Badge tone={ticket.status}>{ticket.status.split("_").join(" ")}</Badge>
          <Badge tone="pending">{ticket.category}</Badge>
        </div>
        <p className="mt-1 max-w-3xl text-sm font-medium text-slate-800">{ticket.subject}</p>
      </div>

      <PageEnter className="grid items-start gap-5 lg:grid-cols-[270px_minmax(0,1fr)] xl:grid-cols-[290px_minmax(0,1fr)_300px]">
        {/* Left: queue list */}
        <PageEnterItem className="order-2 lg:order-1">
          <Card lift={false}>
            <CardHeader title="Queue" desc="Pick up the next ticket." />
            <CardBody className="max-h-[720px] overflow-y-auto">
              <TicketQueue />
            </CardBody>
          </Card>
        </PageEnterItem>

        {/* Center: conversation timeline */}
        <PageEnterItem className="order-1 min-w-0 lg:order-2">
          <div className="space-y-4">
            <Card lift={false}>
              <CardHeader
                title="Conversation"
                desc="Customer request first, then every agent action."
                actions={
                  <MessagesSquare aria-hidden className="h-4 w-4 text-slate-400" />
                }
              />
              <CardBody>
                <ol className="relative space-y-4 border-l-2 border-slate-200 pl-0">
                  <li className="relative pl-6">
                    <span
                      aria-hidden
                      className="absolute -left-[7px] top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-indigo-600 text-[8px] font-bold text-white"
                    >
                      C
                    </span>
                    <div className="rounded-2xl rounded-tl-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6">
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                        Customer · {ticket.code}
                      </p>
                      <p className="mt-1 text-slate-800">{ticket.body}</p>
                    </div>
                  </li>
                  <li className="relative pl-6">
                    <span
                      aria-hidden
                      className="absolute -left-[7px] top-4 h-3.5 w-3.5 rounded-full border-2 border-white bg-emerald-500 shadow"
                    />
                    <div className="ns-card !shadow-none">
                      <div className="ns-card-pad">
                        <ReplyForm ticketCode={ticket.code} />
                      </div>
                    </div>
                  </li>
                  <li className="relative pl-6">
                    <span
                      aria-hidden
                      className="absolute -left-[7px] top-4 h-3.5 w-3.5 rounded-full border-2 border-white bg-slate-300 shadow"
                    />
                    <div className="ns-card !shadow-none">
                      <div className="ns-card-pad">
                        <NoteForm ticketCode={ticket.code} />
                      </div>
                    </div>
                  </li>
                </ol>
              </CardBody>
            </Card>

            {/* Mutation forms */}
            <div id="replacement-form" className="scroll-mt-24">
              <Card lift={false}>
                <div className="ns-card-pad">
                  <ReplacementForm ticketCode={ticket.code} onCreated={refresh} />
                </div>
              </Card>
            </div>
            <div id="refund-form" className="scroll-mt-24">
              <Card lift={false}>
                <div className="ns-card-pad">
                  <RefundForm ticketCode={ticket.code} onCreated={refresh} />
                </div>
              </Card>
            </div>
            <Card lift={false}>
              <div className="ns-card-pad">
                <StatusControl ticketCode={ticket.code} current={ticket.status} />
              </div>
            </Card>
          </div>
        </PageEnterItem>

        {/* Right: context panel */}
        <PageEnterItem className="order-3">
          <div className="space-y-4 xl:sticky xl:top-20">
            <Card lift={false}>
              <CardHeader title="Context" desc="Who · what · which order." />
              <CardBody className="space-y-3 text-sm">
                <div className="flex items-center gap-2.5">
                  <span
                    aria-hidden
                    className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700"
                  >
                    <UserRound className="h-4 w-4" />
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs uppercase tracking-wider text-slate-400">Customer</p>
                    <p className="truncate font-mono text-xs">{ticket.customer_id}</p>
                  </div>
                </div>
                <div className="rounded-xl bg-slate-50 px-3 py-2.5">
                  <p className="text-xs uppercase tracking-wider text-slate-400">Order</p>
                  <p className="mt-0.5 truncate font-mono text-xs">
                    {ticket.order_id ?? "— no linked order —"}
                  </p>
                </div>
                <dl className="grid grid-cols-2 gap-2 text-[13px]">
                  <div className="rounded-xl bg-slate-50 px-3 py-2">
                    <dt className="text-xs text-slate-400">Category</dt>
                    <dd className="font-medium">{ticket.category}</dd>
                  </div>
                  <div className="rounded-xl bg-slate-50 px-3 py-2">
                    <dt className="text-xs text-slate-400">Version</dt>
                    <dd className="font-medium tabular-nums">v{ticket.version}</dd>
                  </div>
                </dl>
                <div className="flex flex-wrap gap-1.5 pt-1 text-[13px]">
                  <Link to="/ops/customers" className="font-medium text-indigo-700 hover:underline">
                    Find customer →
                  </Link>
                  <Link to="/ops/orders" className="font-medium text-indigo-700 hover:underline">
                    Look up order →
                  </Link>
                </div>
              </CardBody>
            </Card>

            <Card lift={false}>
              <CardHeader
                title="Actions"
                desc="Jump to a mutation form."
                actions={<PanelRight aria-hidden className="h-4 w-4 text-slate-400" />}
              />
              <CardBody className="grid gap-2">
                <button
                  type="button"
                  onClick={() => scrollToForm("replacement-form", "repl-order")}
                  className="ns-btn ns-btn-secondary w-full"
                >
                  <History aria-hidden className="h-4 w-4" />
                  New replacement
                </button>
                <button
                  type="button"
                  onClick={() => scrollToForm("refund-form", "refund-order")}
                  className="ns-btn ns-btn-secondary w-full"
                >
                  New refund
                </button>
              </CardBody>
            </Card>
          </div>
        </PageEnterItem>
      </PageEnter>
    </main>
  );
}
