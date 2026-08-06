# Operator guide — pulling a record of a questionnaire portal

Short walkthrough for capturing the questions and our answers out of a vendor
security/due-diligence portal. No technical knowledge needed. You drive the
browser and the sign-in; Claude does the extraction.

## Before you start

Have the portal link and your login for it ready. You need to be able to see the
**completed** questionnaire (the one that's already answered/submitted).

## Steps

1. **Open Claude Code** and start (or continue) a conversation in the DDQ
   Operationalization project.

2. **Open the browser pane.** Click the **browser icon in the top-right** of the
   window. A browser panel opens next to the chat.

3. **Go to the portal and sign in.** Type or paste the portal address into the
   browser pane and log in with your own credentials. Complete any 2-factor step.
   Claude does **not** enter passwords or codes for you — that part is always
   yours.

4. **Open the questionnaire** so the questions are on screen (open the specific
   assessment/response record if the portal lands you on a home page first).

5. **Tell Claude to extract it.** Say something like:
   *"The [customer name] portal is open and I've signed in — please extract the
   questions and our responses."*
   Name the customer (e.g. "Acme Corp") so the file is labeled correctly.

6. **Help it load everything, if asked.** Many portals only show a piece at a time.
   Claude may ask you to **scroll slowly from top to bottom**, or it may click
   through the sections itself. If it asks you to scroll, scroll the questionnaire
   area (not the whole window) all the way down so every question loads.

7. **Get your file.** Claude saves a spreadsheet into the project folder — named
   like `CustomerName_Portal_extract_YYYY-MM-DD.xlsx` — and tells you what's in it:
   how many questions, the answers, the full list of options that were available
   for each question, any comments, and whether any question asked for a file to
   be attached.

## Good to know

- **Claude only reads the portal — it won't change or submit anything.** It won't
  click answers, edit fields, or submit on your behalf. Submitting stays with you.
- **The "options available" column is deliberate.** It shows every choice the
  portal offered for each question, with a mark on the one we picked — handy later
  for spotting where none of the options fit well and we chose the least-bad one.
- **If something looks incomplete** (fewer questions than the portal's own
  progress count), tell Claude — it can re-load the sections and re-check.
- **Nothing to install.** The whole thing happens in the browser pane you already
  opened.
