# Administrator guide

For the person at a real estate company who looks after the CRM: usually the office manager or broker.
No technical knowledge needed.

## First day: "Set up your CRM"

After your first sign-in, **Today** shows a five-step checklist. It disappears when everything is done.

1. **Company profile and logo** (*Settings → Company profile*). The name and logo appear on the sign-in page
   and in the menu. Phone, email, website and address can be used in customer email templates.
2. **Review the settings** (*Settings*). Check the timezone and currency, rename *Lead / Prospect / Client* if
   your office uses other words, and adjust the opportunity stages and follow-up timings. The values you see
   are starting suggestions, not rules. Every change is saved as a new version you can look back at.
3. **Add your people** (*Settings → People → Add user*). Each person gets a temporary password that they must change
   at first sign-in. Tick *Workspace administrator* only for people who should manage accounts and settings.
   Everyone else can still see and work on every customer.
4. **Create a shared pool** (*Settings → Shared pools → Add*). New inquiries that nobody owns yet go here. Pick a
   coordinator (and a backup) who makes sure nothing waits too long.
5. **Bring in your contacts.** Capture them one by one, or use *Contacts → Import CSV* (see below).

## Bringing in an existing contact list

1. In Excel or Google Sheets, make sure the first row has headings such as *Name, Email, Phone, Source,
   Interests, Notes, Lifecycle*. *Download template* on the import page gives you an example.
2. Save as **CSV**.
3. *Contacts → Import CSV*, choose the file and who should be responsible: yourself, or a shared pool.
4. Check the preview. Rows with problems are listed with the reason and are not added. Possible duplicates
   (same email, phone or name as an existing contact) are skipped unless you tick *Also add*.
5. Press *Add contacts*.

Tip for moving a whole team: ask each agent to import their own list. Then every contact starts with the
right person. Alternatively import into a shared pool and let agents claim their clients.

## Keeping accounts safe

- **Two-step sign-in**: each person can turn it on under *Security*. To make it compulsory for everyone, tick
  *Require two-step sign-in* in *Settings*.
- **Lost phone**: open the person in *Settings → People* and press *Turn off two-step sign-in*. They set it up
  again after signing in.
- **Forgotten password**: people can use *Forgot your password?* on the sign-in page if staff email is set up.
  Otherwise open them in *Settings → People* and set a temporary password.
- **Someone leaves the company**: open them in *Settings → People*, untick *Active (can sign in)* and save. They are signed
  out at once. Their clients appear in your **Attention** queue as *Responsible colleague deactivated*. Open
  each client and use *Hand over / release* to give it to a colleague. The colleague accepts it, and until then the
  history shows who was responsible.

## Duplicates

When a contact page shows **Possible duplicates**, open the record you want to keep and press *Merge into
this contact*. You see what will move before you confirm. The merged record is archived, not deleted. If the
two records belong to different people, hand one over first so the same person holds both.

## Customer emails

Automated customer emails (inquiry acknowledgements, onboarding) are shown under *Customer messages*. In
this version they are **captured, not sent**, and labelled "not sent". Edit the wording by opening a template
from the list on the *Customer messages* page.

## Where to look when something seems wrong

| You notice | Look at |
|---|---|
| A yellow bar says the background worker is not running | Tell whoever installed the CRM; reminders wait until it is back, nothing is lost |
| Someone says a reminder did not arrive | *Automation → Jobs* (failed or waiting jobs) |
| You want to know who changed something | *Settings → Audit log* |
| A number on *Reports* looks odd | Click it: every number opens the records behind it |
