"""Ticket invariant: notes, replies, and status moves on the ticket.

Proves the `ticket.note`, `ticket.reply`, and `ticket.status` effects:
new notes carry the expected kind (with the journal mutation key and the
expected body), customer replies are present when required, and the
ticket status equals the contracted target.
"""

from typing import Any

from verifier.verdict import check


def check_invariant(
    contract: dict[str, Any], diff: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    """Ticket outcomes for every ticket effect in the contract."""
    results = []
    added_notes = diff["collections"]["ticket_notes"]["added"]
    tickets = {str(t.get("id")): t for t in after.get("tickets", [])}
    for effect in contract.get("effects", []):
        name = effect.get("effect")
        params = effect.get("params", {})
        if name == "ticket.note":
            results.append(_note_added(added_notes, params, "internal"))
        elif name == "ticket.reply":
            results.append(_note_added(added_notes, params, "customer_reply"))
        elif name == "ticket.status":
            results.append(_status_moved(tickets, params))
    return results


def _note_added(
    added_notes: list[dict[str, Any]], params: dict[str, Any], kind: str
) -> dict[str, Any]:
    """A new note of the expected kind, body, and ticket exists."""
    ticket_id = str(params.get("ticket_id", ""))
    body = params.get("body", "")
    matches = [
        note
        for note in added_notes
        if str(note.get("ticket_id")) == ticket_id and note.get("kind") == kind
    ]
    if not matches:
        return check("ticket.note_present", False, f"ticket {ticket_id}: no new {kind} note")
    if body and not any(note.get("body") == body for note in matches):
        return check("ticket.note_present", False, f"ticket {ticket_id}: {kind} body mismatch")
    keyed = [note for note in matches if note.get("mutation_key")]
    if not keyed:
        return check(
            "ticket.note_present",
            False,
            f"ticket {ticket_id}: {kind} note without mutation key",
        )
    return check("ticket.note_present", True, f"ticket {ticket_id}: new keyed {kind} note")


def _status_moved(tickets: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """The ticket status equals the contracted target."""
    ticket_id = str(params.get("ticket_id", ""))
    want = params.get("to_status", "")
    ticket = tickets.get(ticket_id)
    if ticket is None:
        return check("ticket.status_moved", False, f"ticket {ticket_id} not in scope")
    ok = ticket.get("status") == want
    return check(
        "ticket.status_moved",
        ok,
        f"ticket {ticket_id} is {want}"
        if ok
        else (f"ticket {ticket_id} is {ticket.get('status')!r}, want {want!r}"),
    )
