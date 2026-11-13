# Sales demo script (15 minutes)

For showing the CRM to a real estate company. Uses the fictional demo data, so nothing real is on screen.

## Before the call

```bash
export CRM_DEMO_PASSWORD='choose-a-demo-password'
.venv/bin/python manage.py migrate && .venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver 127.0.0.1:8000   # and in a second terminal: manage.py run_worker
```

Sign in as **Ada Admin** in one browser window and **Ana Reyes** (agent) in a private window. Optionally put
the prospect's name and logo in *Settings → Company profile* so the demo already looks like theirs.

## The story

Open with their pain, in their words: "Leads come in from the website, walk-ins and referrals, and some of
them never get a call back. When an agent leaves, their clients disappear with them."

| Minute | Show | Say |
|---|---|---|
| 0–2 | Ana's **Today** | "Every morning each agent sees who needs them and why: an inquiry nobody answered, a tour with no follow-up, a promise that is due." |
| 2–4 | **Capture contact** as Ana: a walk-in, put in the shared pool | "Front desk captures in under a minute. If it matches someone already in the CRM, it says so before creating a duplicate." |
| 4–5 | **Shared work** as Ben (or Ana): *Claim* | "Shared leads are claimed by exactly one agent. Two people can't grab the same buyer." |
| 5–7 | The client page: log a call, accept the suggested follow-up | "Logging a call takes ten seconds and the next step is suggested for them." |
| 7–9 | **Hand over** to a colleague, then accept as the colleague | "Going on leave? The client is handed over with notes, and the sender stays responsible until the colleague accepts. Nobody falls through the gap." |
| 9–11 | Ada: **Attention** with *Everyone*, then **Reports** and click a number | "The broker sees every relationship that needs someone, by agent, and every number opens the actual clients behind it." |
| 11–12 | **Settings → People**: deactivate an agent, show their clients in Attention | "When someone leaves, their clients show up for you straight away so you can reassign them." |
| 12–13 | **Contacts → Import CSV** with a small file | "Bring your existing spreadsheet on day one." |
| 13–15 | Questions; **Security** page | "Your own server, your own domain, encrypted hourly backups, two-step sign-in. Your data is not shared with other agencies." |

## Questions you will get

| Question | Honest answer |
|---|---|
| Does it send emails to my clients? | It prepares them and shows exactly what would go out. Real sending is switched on per company once their email provider is connected and tested. |
| Is there a mobile app? | It works in the phone's browser; agents can add it to their home screen. |
| Can agents see each other's clients? | Yes, everyone in the office can see every client, so cover and handovers work. Responsibility is always clear. |
| Commission tracking? | Not included. The CRM records opportunities and won value, not payouts. |
| Listings / property inventory? | Not included. Interests and opportunities hold what the client wants. |
| Where is my data? | On a server for your company only, with encrypted backups you hold the key to. |
