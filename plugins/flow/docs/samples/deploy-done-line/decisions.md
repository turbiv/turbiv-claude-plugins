# Decisions — deploy-done-line

## D1 — The footer element and its text

- Kind: made by me
- Recommended: a `<footer class="footer">` element after `<main>`, with the text "Contact:" and a link `<a href="mailto:info@example.com">info@example.com</a>` — a mailto link lets a reader write at once
- Options:
  - A: footer with a mailto link. You get a clickable address. Fails when the reader has no mail client.
  - B: footer with the plain address. You get text only. Fails when the reader wants to click it.
- K1 (changes the request?): no
- K2 (outside the scope?): no
- Cost if wrong: one line to change in review
- Evidence: F1
- Source: plan
- Status: open
