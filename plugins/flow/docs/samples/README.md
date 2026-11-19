# Samples

Sample item folders to try `/flow:validate <path>` by hand. They are not evals; the evals live in
`plugins/flow/evals/`.

| Folder | What it is | Expected result |
|---|---|---|
| `demo-site/` | A tiny static site with a `Makefile`. The specs below point at it (`repos: - ../demo-site`). `make live-check` runs `make deploy` first. | — |
| `deploy-done-line/` | Size S spec. Done line S3 is `make live-check`, which deploys (Done rule 2). | `NOT READY`: a high finding on S3. Often a second high finding: with S3 gone, nothing says who makes the page live |
| `deploy-done-line-clean/` | The same spec. S3 is replaced by person lines: P2 (`make deploy` after merge), P3 and P4 (`curl` the live page). | `READY` |

Run:

```
/flow:validate plugins/flow/docs/samples/deploy-done-line/spec.md
/flow:validate plugins/flow/docs/samples/deploy-done-line-clean/spec.md
```

A path is a check only: the skill writes nothing into these folders.
