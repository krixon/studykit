# Security basics

**Area:** security · **Levels:** graduate → staff+

**One line:** The small set of mistakes that cause most real breaches, and the standard defences that are boring precisely because they work.

## authn-authz

- **Authentication** — who are you? Establishing identity.
- **Authorisation** — what may you do? Checking permission.

They fail differently and the second is where most bugs live. A system with perfect login and no permission check is wide open to anyone who registers.

The classic authorisation bug is **insecure direct object reference**: `GET /orders/1234` returns the order without checking it belongs to the caller. Changing the number reads someone else's data. The fix is to scope every query by the authenticated principal - `WHERE id = ? AND customer_id = ?` - so an unauthorised id returns nothing rather than being caught by a separate check that can be forgotten.

Related: enforce authorisation on the **server**, always. Hiding a button in the UI is not authorisation, and neither is a check in a mobile client you do not control.

Sessions: an opaque session id in an `HttpOnly; Secure; SameSite` cookie, or a short-lived token with a refresh mechanism. Rotate the session id on login to prevent session fixation, and make logout actually invalidate server-side.

## injection

Untrusted input interpreted as code. The same shape recurs in every context:

- **SQL injection** — input concatenated into a query. Fixed **only** by parameterised queries, which send code and data on separate channels. Escaping by hand is a losing game, and an ORM is not automatically safe when you hand it a raw string.
- **Command injection** — input passed to a shell. Pass an argument array to exec rather than building a command line.
- **XSS** — input rendered into HTML and executed by the browser. Fixed by context-aware output encoding; a modern template engine does this by default and disabling it "just here" is how it gets in. `HttpOnly` cookies and a Content Security Policy limit the damage.
- **Path traversal** — input used in a file path, so `../../etc/passwd` escapes the directory. Resolve the path and check it is still inside the permitted root.
- **Deserialisation** — untrusted bytes turned into objects, which in some languages executes code. Never deserialise untrusted input into arbitrary types.

The single principle: **never build an instruction by concatenating a string with untrusted data.** Use the mechanism that separates code from data. Validation is a useful second layer and a poor first one, because a filter you wrote is competing against every encoding trick in existence.

## password-storage

If you must store passwords, hash them with a **slow, salted, memory-hard** algorithm designed for the purpose: Argon2id, scrypt, or bcrypt.

- **Not** MD5 or SHA-256. They are fast by design, which is the wrong property here - a GPU tries billions per second.
- **Salt** per user, stored alongside the hash, so identical passwords produce different hashes and one rainbow table cannot attack everyone.
- **Cost factor** tuned so verification takes ~100 ms on your hardware, and raised as hardware improves.
- Compare with a **constant-time** function; a naive comparison leaks information through timing.

Better still: do not store passwords. Delegate to an identity provider. The most reliable way to avoid leaking credentials is not to hold them.

Modern guidance (NIST) that contradicts old habits: check against known-breached password lists, allow long passphrases and paste, and **do not force periodic rotation** - it produces predictable variations and no measured benefit. Rotate on evidence of compromise.

## secrets

A secret is anything that grants access: API keys, database passwords, signing keys, tokens.

- **Never in source control.** Once committed it is in the history on every clone forever, so rotating is the only real remediation - removing the commit is not enough.
- Inject via environment or a secret manager, and give each environment its own values.
- **Rotate**, and make rotation a routine you have practised, not an emergency procedure you read for the first time during an incident.
- Scope narrowly. A key that can do everything turns any leak into a total compromise.
- Scan commits for secrets automatically, because this will happen eventually.

The related habit: **least privilege** everywhere. An application that only reads should have a read-only database user. Most of the damage in a breach comes from credentials that could do more than the code needed.

## transport

- **TLS everywhere**, including inside your network. "It is internal" assumes an attacker never gets inside, which is the assumption every breach report retires.
- **HSTS** so browsers refuse plain HTTP to your domain after the first visit.
- Validate certificates. Disabling verification to make a test pass is a defect that reliably reaches production.
- TLS protects data **in transit** only. It says nothing about storage, logs, backups, or what the other end does with the data.

Two more that belong in the basic set:

- **CSRF** — a malicious site causes the user's browser to make an authenticated request to yours. Mitigated by `SameSite` cookies and anti-forgery tokens on state-changing requests.
- **Dependencies** — most of your code is someone else's. Automated dependency scanning and prompt patching addresses a genuinely common breach path.

## Related

- [http-and-web](http-and-web.md) — cookies, CORS and the same-origin policy
- [errors-and-logging](errors-and-logging.md) — logs are a leak path
