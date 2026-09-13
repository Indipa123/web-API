# Learn the code in a simple order

These notes help you practise; answer aloud in your own words and run the examples yourself.

1. **Start with `db.py`.** Draw the hierarchy. Explain each foreign key. Find the unique installation/timestamp constraint and both append-only triggers. Predict what happens when an installation with history is deleted.
2. **Read `seed.py`.** Trace one installation through 673 readings. Explain why local time shifts by 5 hours 30 minutes before calculating daylight. Explain why power multiplied by a quarter hour adds energy in kWh. The seed's energy integration is synthetic and approximate.
3. **Read `principal`, `reader`, `provisioner` and `scope` in `main.py`.** Explain how the API determines who called it, then what that caller may do. Authentication and authorization are different checks.
4. **Trace one GET.** Begin at `get_installation`, follow `installation`, then `scope` and `one`. Show where a district restriction becomes part of the SQL.
5. **Trace one POST.** Begin at `ingest`. Follow owner checking, timestamp normalization, energy-neighbor checking and database insertion. Find 201 and Location. Explain why the meter itself cannot retrieve the new reading.
6. **Trace history.** Explain total, page, page_size, next, previous, start/end and sort. Show that the read scope and filters are combined. Explain the stable secondary ordering by row ID when timestamps tie.
7. **Trace caching.** An ETag fingerprints the JSON representation. If-None-Match compares the client's saved version with the current one. A match returns no body and 304. A scope check still happens first.
8. **Trace update protection.** If-Match checks the current installation version before replacement. Explain how a stale edit receives 412 and why a database transaction protects the check and write together.
9. **Trace the district summary.** Explain why stale power is excluded and why cumulative readings are subtracted for daily energy. Describe what missing baseline readings do to coverage.
10. **Explain deployment.** Code runs in a container, traffic enters through HTTPS, and a persistent disk keeps the database. Describe an actual restart test you performed.

## Practice questions

- Why is a meter not another entity? Where does its identifier live?
- What history would be lost if the installation stored only `last_power`?
- What prevents one meter impersonating another installation by changing the URL?
- Can a district reader use the global history endpoint to escape their district?
- Why do duplicate meter timestamps produce 409?
- Does repeating a POST have the same semantics as repeating a PUT or DELETE?
- Why are collections nested but individual resources accessible by their own IDs?
- What makes `overview` composite and `generation-summary` derived?
- What does a 304 response contain? Does it have a JSON body?
- How do you show Level 2 without claiming Level 3?
- What breaks first under nationwide load? How would you measure and address it?
- Which parts did AI generate? Which did you test, change and understand yourself?

If you cannot explain a line, inspect it and experiment before submitting it. Passing automated tests does not replace understanding.
