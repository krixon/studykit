# CSV import endpoint - interviewer notes

**Do not reveal any of this before the attempt.**

A small problem with an unusually high density of real-world traps. Its job is to see whether someone thinks about the unhappy path without being prompted.

## Hidden requirements

- Functional: upload a file, validate rows, create records, report what happened.
- Non-functional: files vary from 10 rows to 500,000, users retry when unsure, the browser will time out on anything slow.
- Deliberately unstated: what happens to a file where row 4000 is invalid, whether re-uploading the same file should duplicate everything, the size limit.

## The questions they should ask

The quality of this attempt is mostly in the questions:

- **All-or-nothing, or best-effort?** This is the biggest fork. All-or-nothing means one transaction and a clean rollback; best-effort means partial success and a report the user must act on. Both are defensible; not choosing is not.
- **What happens on re-upload?** Users retry when they are unsure whether it worked. Without a natural key or an idempotency key, a nervous user creates 400 duplicate customers.
- **How big can the file be?** Decides whether this is synchronous at all.

## Back-of-envelope they should reach

- 500,000 rows at ~200 bytes is 100 MB. Reading it entirely into memory is a real risk, and streaming is not hard.
- At 1 ms per insert, 500,000 rows is over eight minutes - far past any HTTP timeout. Batch inserts bring that to seconds.
- The number that forces an asynchronous design is the browser timeout, typically 30-60 seconds.

## Deep dives (pick two)

1. **Synchronous versus asynchronous.** Small files can be handled in-request. Large ones need: accept the file, return a job id, process in the background, let the client poll or receive a webhook. Push on what the user sees while waiting and how they learn it failed.
2. **Error reporting.** A single "invalid file" message is useless for a 400-row file with three bad rows. What works is a per-row report with the row number, the field, and the rule that failed - ideally a downloadable CSV of just the failures so the user can fix and re-upload only those.
3. **Parsing.** Do not split on commas. Quoted fields contain commas and newlines; encoding is often not UTF-8 for files that came from a spreadsheet; the header row may be absent or reordered. A library handles this and hand-rolled code does not.
4. **Idempotency.** Either a natural unique key (email) with an explicit insert-or-update decision, or a client-supplied import id so a retry of the same upload is recognised.

## Strong-answer signals

- Asks all-or-nothing versus best-effort before designing anything.
- Streams rather than loading the whole file, and says why.
- Per-row error reporting with row numbers.
- Notices the retry problem and handles duplicates deliberately.
- Bounds the file size and says what happens past the bound.
- Validates before writing anything, or writes in a transaction, rather than discovering the problem halfway through.

## Common traps

- Splitting on commas.
- Loading the whole file into memory with no size limit.
- One insert per row inside a loop, inside a request.
- Returning "import failed" with no indication of which row.
- No thought about what a second upload of the same file does.
- Assuming UTF-8 without checking, then producing mojibake in the customer names.

## Follow-ups

- Row 4000 of 5000 is invalid. What happens to rows 1 to 3999?
- The user uploads the same file twice because the first response was slow. What is in the database?
- The file is 300 MB. Where does your design break?
- A name comes out as JosÃ©. What went wrong and where?
- How would you let the user check the file is correct before committing anything?
