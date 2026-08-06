# Data and encoding

**Area:** data · **Levels:** graduate → staff+

**One line:** The representation problems - text, time, numbers - that look trivial and produce a steady supply of production bugs.

## text-encoding

A **character set** maps characters to numbers (code points). An **encoding** maps those numbers to bytes. Unicode is the character set; UTF-8 is the encoding.

- **UTF-8** is variable width: 1 byte for ASCII, up to 4 for anything else, and it is backward compatible with ASCII. Use it everywhere, and set it explicitly rather than relying on a platform default that differs between your laptop and the server.
- **Mojibake** - `caf√©` where `café` should be - is text encoded one way and decoded another. The fix is never to re-encode the mangled output; find the point where the wrong decoding happened.
- A **string is not an array of characters** in any useful sense. `len()` may return bytes, UTF-16 code units, or code points depending on the language, and none of those is what a user calls a character. `é` can be one code point or two (e plus combining accent); an emoji with a skin tone modifier is several. Truncating a string to N "characters" can split a character in half.
- **Normalisation** (NFC) makes the two spellings of `é` comparable. Compare and store normalised, or "café" will not match "café".

## time-and-zones

The single most reliable source of subtle bugs.

- **Store UTC, display local.** Convert at the boundary and never earlier.
- A timestamp with no zone is ambiguous, and the ambiguity resolves differently on your machine than in production.
- **Time zone offsets change.** Daylight saving means the offset for a location depends on the date, so storing "+01:00" is not the same as storing "Europe/London". For a **future** event, store the zone name and the local time - if a government moves the DST date, a meeting at 09:00 should still be at 09:00.
- Local time is not continuous: an hour is skipped in spring and repeated in autumn, so some local times do not exist and some occur twice.
- **Do not do date arithmetic in seconds.** "One month later" is not 30 days, and "tomorrow at 09:00" is not "now plus 24 hours" across a DST boundary. Use the library's calendar arithmetic.
- Never trust a client's clock for anything that matters. It can be wrong by hours and can be set deliberately.
- Leap seconds and leap years exist; February 29 breaks naive "same day next year" code annually.

## numbers-money

- **Floating point cannot represent 0.1 exactly**, so `0.1 + 0.2 != 0.3`. This is not a language bug, it is binary fractions.
- **Never use a float for money.** Use a decimal type, or store integer minor units (pence, cents) and format at the edges. Rounding errors in a financial system are not cosmetic.
- Rounding has to be **specified**: half-up, half-even (banker's rounding, which avoids systematic bias), or truncation. Two systems using different rules will disagree by pennies, and reconciling those pennies costs more than choosing correctly.
- **Integer overflow** wraps silently in some languages and raises in others. A 32-bit seconds timestamp overflows in 2038.
- **Integer division** truncates. `5 / 2` is 2 in many languages, and the resulting off-by-one is easy to miss.
- JSON numbers are doubles in JavaScript, so an integer id above 2⁵³ loses precision. **Send large ids as strings.**

## serialisation

Turning structures into bytes and back.

| Format | Strength | Weakness |
|---|---|---|
| **JSON** | universal, human-readable | no schema, no date type, no integer/float distinction, verbose |
| **CSV** | universal, trivial to produce | no types, quoting and newline rules are a minefield, no standard |
| **Protobuf / Avro** | compact, schema-enforced, evolvable | needs tooling and a schema registry, not human-readable |
| **XML** | schema and namespaces | verbose, and its parsers have a long security history |

The parts people get wrong:

- **Schema evolution.** Adding an optional field is safe. Removing one, renaming one, changing a type, or making an optional field required is not - and during a rolling deploy both versions are live at once, so a change must be safe in both directions.
- **Unknown fields.** A consumer must ignore fields it does not recognise, or you can never add anything.
- **CSV is not a format.** It is a family of conventions differing in delimiter, quoting, escaping, encoding and line endings. Use a library; a comma inside a quoted field will find your hand-rolled split.

## validation

- **Validate at the boundary**, once, as data enters the system. Then the interior can trust its own types instead of re-checking defensively everywhere.
- **Parse, do not validate**: convert input into a type that cannot represent the invalid state (an `Email` type rather than a checked string), so the check cannot be forgotten downstream.
- **Allow-lists beat deny-lists.** Enumerating what is permitted is finite; enumerating what is forbidden is not.
- Validate on the **server** regardless of what the client checks. Client validation is a user-experience feature.
- Reject with a message naming the field and the rule. "Invalid input" costs a support ticket.
- Bound everything that can grow: string length, array size, request body size, upload size, page size. An unbounded input is a denial-of-service vector and, eventually, a memory error.

## Related

- [security-basics](security-basics.md) — validation is a security boundary
- [errors-and-logging](errors-and-logging.md) — how to report a rejection usefully
