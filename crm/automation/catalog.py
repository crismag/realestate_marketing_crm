"""Rule catalog (from context/04_requirements/AUTOMATION_CATALOG.md, PROP-035).

Behaviour is implemented in engine.py; these records describe it so users can
inspect trigger, conditions, action and stop policy on the Automation screen.
Enabled flags and config are implementation defaults and stay configurable.
"""

RULES = [
    {
        "key": "inquiry", "name": "New inquiry alert", "audience": "internal",
        "trigger": "A customer inquiry is recorded (capture form, repeat inquiry or intake).",
        "conditions": "Inquiry is still awaiting a response when the job runs.",
        "action": "Notify the current handler, or the pool coordinator(s) if the client is pool-held.",
        "stop_policy": "Skipped if already responded/closed. One alert per inquiry. No coordinator = routing gap shown.",
    },
    {
        "key": "after-tour", "name": "Toured client without follow-up", "audience": "internal",
        "trigger": "Attention sweep (every few minutes).",
        "conditions": "Last tour/viewing is older than the after-tour window and no follow-up interaction was logged since.",
        "action": "Notify the current handler (or pool coordinator).",
        "stop_policy": "Logging any follow-up resolves it. One alert per tour. Snoozed reasons are skipped.",
    },
    {
        "key": "inactivity", "name": "Inactive relationship", "audience": "internal",
        "trigger": "Attention sweep.",
        "conditions": "Last qualifying contact is older than the lifecycle cadence; no customer-agreed later contact date.",
        "action": "Notify the current handler (or pool coordinator).",
        "stop_policy": "A new qualifying interaction resolves it. One alert per inactivity episode. Profile views never count.",
    },
    {
        "key": "missing-next", "name": "Next action missing", "audience": "internal",
        "trigger": "Attention sweep.",
        "conditions": "Active lead/prospect with no open task and no agreed contact date.",
        "action": "Prompt the current handler (or pool coordinator).",
        "stop_policy": "Creating a task resolves it. One prompt per episode.",
    },
    {
        "key": "task-due", "name": "Task overdue reminder", "audience": "internal",
        "trigger": "Attention sweep.",
        "conditions": "An open task's due time has passed.",
        "action": "Remind the task assignee (who may differ from the client handler).",
        "stop_policy": "Completing or replanning the task stops it. One reminder per due time.",
    },
    {
        "key": "task-assigned", "name": "Task assigned to you", "audience": "internal",
        "trigger": "A colleague creates or reassigns a task to someone else.",
        "conditions": "Task is still open and still assigned to that person.",
        "action": "Notify the new assignee.",
        "stop_policy": "Skipped if the task closed or moved again before delivery.",
    },
    {
        "key": "handover", "name": "Handover acceptance request", "audience": "internal",
        "trigger": "A client transfer is requested; sweep for transfers pending beyond the window.",
        "conditions": "Handover still awaiting acceptance.",
        "action": "Ask the recipient to accept; remind the sender they remain responsible (ADR-001).",
        "stop_policy": "Accepted, declined, cancelled or stale handovers stop reminders. One reminder per day.",
    },
    {
        "key": "pool-release", "name": "Pool release review", "audience": "internal",
        "trigger": "An agent requests release of a client to a pool.",
        "conditions": "Release still awaiting coordinator acceptance.",
        "action": "Notify the pool coordinator and backup (ADR-002).",
        "stop_policy": "Same as handover. The agent stays responsible until accepted.",
    },
    {
        "key": "watch", "name": "Watched client activity", "audience": "internal",
        "trigger": "Inquiry, interaction, lifecycle, assignment or task completion on a watched client.",
        "conditions": "User still watches the client; the user did not cause the change.",
        "action": "Notify watchers. Watching never changes responsibility.",
        "stop_policy": "Unwatching stops further alerts. One alert per event per watcher.",
    },
    {
        "key": "digest", "name": "Daily attention digest", "audience": "internal",
        "trigger": "Daily at the configured digest hour (workspace timezone).",
        "conditions": "User has at least one active attention item routed to them.",
        "action": "One in-app digest per user per day, plus a staff-only mail copy when that setting is on. Never a customer message.",
        "stop_policy": "Recipients and counts are re-evaluated at send time. One digest per user per day; missed days are not back-filled. Staff digest email off skips the staff copy, including one still waiting.",
    },
    {
        "key": "escalation", "name": "Overdue escalation", "audience": "internal",
        "trigger": "Attention sweep.",
        "conditions": "A task is overdue by more than the escalation threshold.",
        "action": "Alert configured escalation recipients. Ownership is never removed automatically (ADR-002).",
        "stop_policy": "Completion or replanning stops it. One escalation per task due time. No recipients = routing gap.",
    },
    {
        "key": "customer-followup", "name": "Inquiry acknowledgement email", "audience": "customer",
        "trigger": "A customer inquiry is recorded.",
        "conditions": "Customer has an email address, has not opted out, and the inquiry is still awaiting a personal response.",
        "action": "Send the 'inquiry-ack' template through the configured transport (sandbox by default).",
        "stop_policy": "Stops on reply, response, opt-out, archive, rule disabled (queued messages are cancelled), "
                       "frequency cap; deferred during quiet hours.",
    },
    {
        "key": "onboard", "name": "Client onboarding email", "audience": "customer",
        "trigger": "Contact becomes a client (implementation default: an opportunity is won).",
        "conditions": "Customer has an email address and has not opted out.",
        "action": "Send the 'onboarding' template through the configured transport (sandbox by default).",
        "stop_policy": "One onboarding email per contact. Opt-out, archive, disabled rule and frequency cap stop it.",
    },
]

TEMPLATES = [
    {
        "key": "inquiry-ack", "name": "Inquiry acknowledgement",
        "subject": "Thanks for your inquiry, {{ customer_name }}",
        "body": "Hello {{ customer_name }},\n\nThank you for contacting {{ workspace_name }}. "
                "{{ handler_name }} will get back to you shortly.\n\nKind regards,\n{{ workspace_name }}",
    },
    {
        "key": "onboarding", "name": "Client onboarding",
        "subject": "Welcome, {{ customer_name }}",
        "body": "Hello {{ customer_name }},\n\nWelcome aboard. {{ handler_name }} is your contact at "
                "{{ workspace_name }} and will guide you through the next steps.\n\nKind regards,\n{{ workspace_name }}",
    },
]
