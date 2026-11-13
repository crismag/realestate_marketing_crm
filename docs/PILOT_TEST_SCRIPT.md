# Guided pilot test (about 30 minutes)

Use this to try the CRM yourself or with one or two friendly agents before showing it to a customer
company. Everything runs on fictional demo data and nothing is emailed to anyone.

## Setup (5 minutes, once)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
export CRM_DEMO_PASSWORD='pick-a-demo-password'
.venv/bin/python manage.py migrate && .venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver 127.0.0.1:8000      # terminal 1
.venv/bin/python manage.py run_worker                     # terminal 2
```

Open http://127.0.0.1:8000. Use a normal window for one person and a private window for another.

| Person | Email | Plays |
|---|---|---|
| Ana Reyes | ana@demo.example.test | Sales agent |
| Ben Santos | ben@demo.example.test | Sales agent |
| Cora Lim | cora@demo.example.test | Pool coordinator |
| Max Cruz | max@demo.example.test | Sales manager |
| Ada Admin | admin@demo.example.test | Office administrator |

## Tasks

Write down anything that confuses you, takes more than two clicks to find, or looks wrong.

1. **Morning check (Ana).** Open *Today*. Can you tell in ten seconds which client needs you first, and why?
2. **New walk-in (Ana).** *Capture contact*: a walk-in buyer looking for a 2-bedroom condo. Put them in the
   shared pool. Did the form ask for anything you would not know at the front desk?
3. **Claim (Ben).** In *Shared work*, claim the walk-in. Try to claim it again as Ana in the other window. You
   should see who already has it.
4. **First call (Ben).** On the client page, log a call where you reached the customer. Accept the suggested
   follow-up task or set your own date.
5. **Tour (Ben).** Log a tour as an interaction. Then add an opportunity with a price and move it to
   *Viewing*.
6. **Going on leave (Ben).** Hand the client over to Ana with a reason. Check that Ben is still responsible
   until Ana accepts, then accept as Ana.
7. **Manager view (Max).** Open *Attention* with "Everyone" and then *Reports*. Click a number and check it
   leads to the right clients.
8. **Agent leaves the company (Ada).** In *Settings → People*, deactivate Ben. Read the warning, then open
   *Attention*: Ben's clients appear under "Responsible colleague deactivated". Start a handover to Ana from
   one of those client pages, and accept it as Ana.
9. **Company setup (Ada).** In *Settings*, change the workspace name, timezone and currency to your own. Rename
   "Lead/Prospect/Client" if your company uses other words. Check the contact list uses the new words.
10. **Customer email (Ada).** Open *Customer messages*. Every message is marked "not sent (sandbox)". Nothing
    left the computer.

## What to send back

- The step number and what you expected versus what happened.
- A screenshot if something looked broken, especially on a phone.
- Anything a real estate office would expect that is missing.
