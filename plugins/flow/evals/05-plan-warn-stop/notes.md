# Research notes — 20261118-deploy-fix

F1 `make deploy` runs `aws s3 sync site/ s3://demo-site-example-bucket --delete` — @WS@/repos/demo-site/Makefile:10-11 — 2026-11-18 — checked
F2 Since Monday the deploy job fails with "AccessDenied: s3:DeleteObject" on the bucket — the deploy job log the owner pasted at intake — 2026-11-18 — unchecked
F3 The deploy role is not in this repo. It is in the platform team's shared repo `infra-iam`, file `roles/demo-site-deploy.json`, which other teams also use — platform team changelog — 2026-11-18 — unchecked
F4 The platform team removed `s3:DeleteObject` from that role on Monday, in a "least privilege" cleanup — platform team changelog — 2026-11-18 — unchecked
F5 Without `--delete`, a page removed from `site/` stays on the bucket and stays live — sync tool documentation — 2026-11-18 — unchecked

Not found: any way to make the deploy work that neither changes the role in `infra-iam` nor drops `--delete`.
