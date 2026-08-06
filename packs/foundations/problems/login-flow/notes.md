# Login and session flow - interviewer notes

**Do not reveal any of this before the attempt.**

Everyone has built this and few have built it correctly. The point is to see whether the standard defences are known as a set, rather than remembered one at a time.

## Hidden requirements

- Functional: register, log in, stay logged in, log out, reset a forgotten password.
- Non-functional: credentials must survive a database breach, a stolen session must be revocable, brute force must be impractical.
- Deliberately unstated: multi-factor, whether logout must be immediate everywhere, session lifetime, mobile clients.

## The path they should walk

1. **Storage.** Argon2id, scrypt or bcrypt, per-user salt, cost tuned to ~100 ms. Not SHA-256, not MD5, not encryption (which is reversible, and the key is on the same machine).
2. **Verification.** Constant-time comparison. The same generic error and, ideally, the same response time for a wrong password and an unknown email, or the endpoint becomes a user enumeration oracle.
3. **Session.** A cryptographically random id, or a signed short-lived token with a refresh mechanism. **Rotate the session id on login** - reusing a pre-login id is session fixation.
4. **Cookie.** `HttpOnly`, `Secure`, `SameSite=Lax` at least. Ask them what each one stops; a candidate who can name all three and their attacks is doing well.
5. **Brute force.** Rate limit per account and per IP, with the per-account limit being the one that matters and the per-IP limit being the one that is easy to evade. Exponential delay or lockout, and be aware lockout is itself a denial-of-service vector against a known user.
6. **Reset.** A single-use, time-limited, high-entropy token, sent to the email, invalidating existing sessions on use. The reset endpoint must return the same response whether or not the address exists.

## Deep dives (pick two)

1. **Session versus token.** Server-side session means immediate revocation and a lookup per request. A self-contained token means no lookup and hard revocation - a valid token is valid until it expires. Push on how they log someone out of all devices under each model.
2. **User enumeration.** Different messages, different status codes, or different timings for unknown-email versus wrong-password all leak which addresses are registered. Genuinely hard to close completely, because registration and password reset leak it too.
3. **CSRF.** With cookie-based sessions, another site can cause the browser to make an authenticated request. `SameSite` plus anti-forgery tokens on state-changing requests.

## Strong-answer signals

- Names a password-specific KDF and knows why fast hashes are wrong.
- Rotates the session id on login without being asked.
- Names all three cookie flags and the attack each addresses.
- Treats the reset flow as part of authentication, not an afterthought - it is a login path.
- Considers logging out other devices, and notices it is easy with sessions and hard with tokens.
- Mentions not storing passwords at all, by delegating to an identity provider.

## Common traps

- SHA-256 with no salt, or a salt shared across users.
- "Email not found" versus "wrong password" as distinct messages.
- No rate limiting on the login endpoint.
- A password reset token that is guessable, long-lived, or reusable.
- Not rotating the session on login.
- Logging the password, or the full request body, on a failed login.

## Follow-ups

- Your database leaks. What can the attacker do with what they have?
- A user says log me out everywhere. What happens under your design?
- How do you stop someone trying a million passwords against one account?
- The reset email arrives 40 minutes late. Is the link still valid, and should it be?
- Add "remember me" for 30 days. What changes, and what new risk have you taken on?
