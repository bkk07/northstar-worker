"""Chat intent parser: deterministic classification without a database."""

from app.services.worker.chat_intent import parse_intent


def test_solve_ticket_with_code():
    """'Solve ticket TCK-...' routes to a run launch."""
    intent = parse_intent("Please solve ticket TCK-ABC123, the laptop arrived damaged")
    assert intent.kind == "solve_ticket"
    assert intent.ticket_code == "TCK-ABC123"


def test_short_seed_codes_match():
    """Seed codes like TCK-102 (3 chars) parse too."""
    intent = parse_intent("solve ticket TCK-102")
    assert intent.kind == "solve_ticket"
    assert intent.ticket_code == "TCK-102"


def test_solve_verbs_all_route():
    """Every solve verb maps to the same intent."""
    for verb in ("handle", "fix", "work on", "resolve", "take care of"):
        intent = parse_intent(f"{verb} TCK-XYZ9")
        assert intent.kind == "solve_ticket", verb


def test_bare_code_is_status_lookup():
    """A lone ticket code asks for state, never launches a run."""
    intent = parse_intent("TCK-ABC123")
    assert intent.kind == "ticket_status"
    assert intent.ticket_code == "TCK-ABC123"


def test_status_of_ticket():
    """Explicit status questions route to the ticket summary."""
    intent = parse_intent("What is the status of TCK-ABC123?")
    assert intent.kind == "ticket_status"


def test_status_of_task_uuid():
    """Full task ids route to the task summary."""
    task_id = "765aeb7e-8632-48f2-bf61-ea6211ba4d7d"
    intent = parse_intent(f"status of {task_id}")
    assert intent.kind == "task_status"
    assert intent.ref == task_id


def test_status_of_latest_task():
    """'My last task' resolves to the newest task."""
    intent = parse_intent("how is my last task doing?")
    assert intent.kind == "task_status"
    assert intent.ref == "latest"


def test_list_open_tickets():
    """Queue questions route to the ticket list."""
    assert parse_intent("show open tickets").kind == "list_tickets"
    assert parse_intent("what tickets are open?").kind == "list_tickets"


def test_approve_attempt_refused():
    """Bare approvals route to the refusal (safety: chat never decides)."""
    assert parse_intent("yes, approve it").kind == "approve_attempt"
    assert parse_intent("go ahead").kind == "approve_attempt"


def test_help_and_unknown():
    """Help asks and gibberish both answer with guidance."""
    assert parse_intent("what can you do?").kind == "help"
    assert parse_intent("hello there, bot").kind == "unknown"


def test_ticket_detail_questions():
    """Detail questions about a ticket route to the rich summary."""
    assert parse_intent("tell me about TCK-ABC123").kind == "ticket_detail"
    assert parse_intent("show me TCK-102 with its order").kind == "ticket_detail"
    assert parse_intent("TCK-ABC123").kind == "ticket_status"


def test_order_detail_lookup():
    """Order codes route to the order summary."""
    intent = parse_intent("show order ORD-1943")
    assert intent.kind == "order_detail"
    assert intent.order_code == "ORD-1943"


def test_product_detail_lookup():
    """SKUs route to the product + policy summary."""
    intent = parse_intent("what is the policy for HP-01?")
    assert intent.kind == "product_detail"
    assert intent.sku == "HP-01"


def test_policy_answer():
    """Bare policy questions route to the headline policies."""
    assert parse_intent("what is the refund policy?").kind == "policy_answer"


def test_approvals_list():
    """Approval-queue questions route to the pending list."""
    assert parse_intent("anything waiting for approval?").kind == "approvals_list"
    assert parse_intent("show pending approvals").kind == "approvals_list"
