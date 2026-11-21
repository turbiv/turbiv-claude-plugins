# Reddit data access policy and timeline for a free, keyless, personal research tool (as of 2026-11-20)

Source-quality legend used below:
- **[NEWS]** independent news outlet (heise, Decrypt, PPC Land).
- **[MIRROR/QUOTE]** Reddit's own post text, seen only through a mirror, a watchdog site, or a GitHub issue that quotes it. reddit.com, redditinc.com and support.reddithelp.com could not be fetched directly: all returned HTTP 403 or were blocked.
- **[VENDOR]** blog from a company that sells Reddit data, scraping or API access (redditapis.com, bigideasdb.com, THINKPOL, Crawlora, Data365, fetchlayer, etc.). These have a commercial interest in saying the official route is dead.

## Dated master timeline

| Date | Event | Confidence |
|---|---|---|
| May 2023 | Pushshift loses public access; restricted to approved moderators | [VENDOR] THINKPOL; consistent with widely known history |
| 2023-07-01 | Free tier rate limits enforced: 100 QPM per OAuth client ID; 10 QPM without OAuth | [VENDOR/guide] zuplo, citing Reddit's 2023 r/redditdev post |
| 2025-10-22 | Reddit sues SerpApi, Oxylabs, AWMProxy and Perplexity over scraping | [NEWS] PPC Land |
| 2025-11-11 | Responsible Builder Policy: self-service API access closed, all new access needs explicit approval | [MIRROR/QUOTE] r/redditdev mirror plus a reddithelp mirror (search snippets only) |
| 2026-03-25 / 03-31 | "App" label policy for automated accounts is announced and takes effect | [NEWS] PPC Land; [VENDOR] THINKPOL |
| 2026-05-28 | r/modnews post "Protecting communities from scrapers and platform abuse" announces the shutdown of unauthenticated `.json` endpoints | [VENDOR] Crawlora/dev.to, THINKPOL; [NEWS] PPC Land says "around June 2026" |
| late May 2026 (one vendor says 05-30) | Anonymous `.json` requests start returning 403 | [VENDOR] only |
| 2026-06-30 | Reddit announces that Old Reddit will require login | [VENDOR] THINKPOL; [NEWS] PPC Land ("earlier in 2026") |
| Aug 2026 | Developer Platform migration plan announced; developers asked to register | [NEWS] PPC Land, Decrypt |
| 2026-09-30 | r/modnews and r/redditdev posts give the full schedule (RSS, Data API, Old Reddit) | [NEWS] Decrypt, heise, PPC Land; [MIRROR/QUOTE] redditwatch.org |
| 2026-10-31 | New public API access requests no longer accepted | [NEWS] Decrypt, PPC Land; [MIRROR/QUOTE] |
| 2026-11-12 | r/redditdev reminder post restates "March 2027: Remaining public API access ends" | [MIRROR/QUOTE] GitHub issue |
| 2026-11-13 | RSS feed support ends (announced; real-world effect not verified) | [NEWS] Decrypt, heise; [MIRROR/QUOTE] |
| 2026-11-30 | Registration closes for the $1M App Migration Program | [NEWS] Decrypt, PPC Land |
| 2027-01-12 | API access removal starts for apps and users that are not registered or have not answered outreach | [NEWS] Decrypt, PPC Land; [MIRROR/QUOTE] |
| March 2027 (no day given) | Remaining public Data API access ends | [NEWS] Decrypt, heise, PPC Land; [MIRROR/QUOTE] |

## Responsible Builder Policy (Nov 2025): what it requires and how new API apps get approved

### Takeaway
Since about 2025-11-11, getting any new Reddit Data API credential has required explicit, manual approval under the Responsible Builder Policy; self-service app creation was closed. As of 2026-10-31, even that request route is closed for new public API access, so a new personal tool cannot get a fresh OAuth key.

### Cited Findings
- The policy's help-center article says you must request access and get explicit approval before using Reddit data through the API. It covers developers, moderators, researchers and apps, and lists penalties including revoked access tokens and suspended apps or accounts. Seen only via a search snippet of a mirror; the direct fetch and the mirror both returned 403. — [Responsible Builder Policy (mirror of support.reddithelp.com article 42728983564564)](https://kapook.pages.dev/bl-https://support.reddithelp.com/hc/articles/42728983564564)
- The r/redditdev announcement, "Introducing the Responsible Builder Policy", is dated 2025-11-11. In it Reddit said self-service access to the public Data API would be closed, and that existing access would not be affected for those within policy. It sent developers to Devvit, researchers to a ticket for r/reddit4researchers, and moderators to a request form when Devvit cannot cover their need. Seen via search snippets of a mirror only; the direct fetch returned 403. — [r/redditdev mirror](https://r.datuan.dev/r/redditdev/comments/1oug31u/introducing_the_responsible_builder_policy_new/noh6fun)
- Commenters in that thread report rejections with a generic message citing "non-compliance and/or missing details", with no further clarification. These are anecdotal and only seen in search snippets. — [r/redditdev mirror comment](https://r.datuan.dev/r/redditdev/comments/1oug31u/introducing_the_responsible_builder_policy_new/npx2fbl/?context=3)
- In 2026, apps must follow the Responsible Builder Policy as one of the terms for registration and migration. PPC Land (published 2026-10-04) names the policy but gives no detail on it. — [PPC Land](https://ppc.land/reddit-to-halt-public-data-api-access-in-march-2027-as-14-000-apps-register/)
- A third-party guide dates the policy to 11 Nov 2025. [VENDOR], and the site says it is not affiliated with Reddit. — [redditapis.com](https://www.redditapis.com/blogs/reddit-bot-rules-2026)

### Inferences
- For a new personal tool in Nov 2026, the approval route is moot: requests closed on 2026-10-31 (next section). Only credentials approved before then keep working, and only until 2027-01-12 if unregistered, or March 2027 at the latest.
- The guidance to use Devvit points toward apps that run inside Reddit, not off-platform research tools. Devvit supports TypeScript, not Python, per [PPC Land](https://ppc.land/reddit-to-halt-public-data-api-access-in-march-2027-as-14-000-apps-register/).

### Gaps
- I could not read the full policy text. Both support.reddithelp.com and its mirrors returned 403. The exact rules on AI training, deleted content, data retention and rate-limit circumvention are therefore unverified.
- I found no official approval-time numbers or approval rates.

## Did Reddit stop accepting new Data API requests on 2026-10-31, and does public access end in March 2027?

### Takeaway
**Confirmed.** Several independent outlets report a 2026-09-30 announcement in r/modnews and r/redditdev. Under it, new public API access requests stopped on 2026-10-31, unregistered apps start losing access on 2027-01-12, and remaining public API access ends in March 2027. A 2026-11-12 r/redditdev reminder restated the March 2027 date. Partners with written agreements may be exempt.

### Cited Findings
- **Primary posts** (URLs as listed by a watchdog site; not fetched directly):
  - r/redditdev "Moving Data API Apps to the Developer Platform: migration dates and next steps", u/boat-botany, 2026-09-30: https://www.reddit.com/r/redditdev/comments/1wubcvf/moving_data_api_apps_to_the_developer_platform/
  - r/modnews "Continuing our infrastructure updates: What's changing in the coming months", u/judy-funnie, 2026-09-30: https://www.reddit.com/r/modnews/comments/1wubgvt/continuing_our_infrastructure_updates_whats/
  - r/modnews "Mod Monthly: Your October 2026 newsletter is here", u/mod_lab: https://www.reddit.com/r/modnews/comments/1x6rjnd/mod_monthly_your_october_2026_newsletter_is_here/
  - Source for all three: [Reddit Watch](https://redditwatch.org/issues/reddit-rss-shutdown-public-api-closure-2026)
- Reddit's wording, as quoted by Reddit Watch: "New requests for public API access will no longer be accepted" (2026-10-31), and "Over 14,000 apps and bots have registered". — [Reddit Watch](https://redditwatch.org/issues/reddit-rss-shutdown-public-api-closure-2026)
- On 2026-11-15, a GitHub issue quoted the r/redditdev post: "API access starts to close for apps and users that haven't registered or responded to our outreach." and "Public access will close for all remaining apps and users." It also cites the 2026-11-12 r/redditdev reminder (https://www.reddit.com/r/redditdev/comments/1xulk8k/) with "March 2027 | Remaining public API access ends." — [jordanallenlewis/reddit-research-mcp issue #11](https://github.com/jordanallenlewis/reddit-research-mcp/issues/11)
- Decrypt (published 2026-10-01) reports the same schedule: 2026-10-31 for new requests, 2027-01-12 for unregistered apps, March 2027 for all remaining public API access. It also reports the $1M App Migration Program, which pays $1,000 per eligible migrated app with applications due 2026-11-30, and Reddit's rationale of scraping and "automated abuse". — [Decrypt](https://decrypt.co/379892/reddit-killing-rss-feeds-public-api-access-ai-scrapers)
- heise (published 2026-10-01) says the public API ends by March 2027, and that "Registered API users are not affected" (paraphrase). It adds that AI providers using Reddit content via the API will need a commercial contract. — [heise](https://www.heise.de/en/news/Reddit-to-shut-down-RSS-feeds-and-public-API-11473400.html)
- PPC Land (published 2026-10-04) adds three points:
  - Partners with written agreements, such as accessibility apps and mobile clients like Narwhal, may keep public API access.
  - u/KeyserSosa wrote "It honestly won't happen this year."
  - There was a 2026-11-10 migration progress update, and a 2027-02-23 progress update is planned.
  - Source: [PPC Land](https://ppc.land/reddit-to-halt-public-data-api-access-in-march-2027-as-14-000-apps-register/)
- **Conflict / nuance:** heise says registered users are "not affected". The GitHub issue's own analysis, dated 2026-11-16, says registration is *not* expected to keep access past March 2027; registration mainly avoids the early 2027-01-12 cutoff. — [heise](https://www.heise.de/en/news/Reddit-to-shut-down-RSS-feeds-and-public-API-11473400.html); [GitHub issue #11](https://github.com/jordanallenlewis/reddit-research-mcp/issues/11)
- **State as of 2026-11-15:** a live check found anonymous `search_reddit` and `get_post` in reddit-research-mcp still working. That mode borrows redditwarp's installed-app client ID rather than an app the maintainer owns, and the maintainer flags that it may not survive 2027-01-12. — [GitHub issue #11](https://github.com/jordanallenlewis/reddit-research-mcp/issues/11)

### Inferences
- A keyless tool cannot get its own credentials now. Borrowing another project's client ID, as redditwarp's installed-app ID is borrowed above, is technically possible until about Jan to Mar 2027. It is very likely outside what the Responsible Builder Policy permits, and it will stop working by March 2027 in any case.
- "Written agreement" exemptions are not available to individual personal tools in practice.

### Gaps
- The exact day in March 2027 has not been announced.
- The original r/redditdev post body could not be read directly. Quotes come through Reddit Watch, the GitHub issue and news outlets.
- It is unclear whether "remaining public API access" includes personal "script"-type OAuth apps used by a single user. No source addresses that category explicitly.

## Reddit RSS feeds ending 2026-11-13

### Takeaway
**Confirmed as announced.** On 2026-09-30, Reddit said it would stop supporting RSS feeds on 2026-11-13, citing scraping and automated abuse. It said there is "no replacement" for RSS use outside communities you moderate. I could not verify from an independent source what feeds actually return after 2026-11-13.

### Cited Findings
- Reddit's quoted wording: "we'll stop supporting RSS feeds on November 13, 2026"; "Because RSS is now a common surface for large-scale scraping and automated abuse"; "If you use RSS for feeds outside of a community you moderate, there is no replacement." Moderators are pointed to "Devvit apps like Discord Relay". — [Reddit Watch](https://redditwatch.org/issues/reddit-rss-shutdown-public-api-closure-2026)
- Decrypt (2026-10-01) confirms the 2026-11-13 date, the no-replacement statement and Discord Relay. — [Decrypt](https://decrypt.co/379892/reddit-killing-rss-feeds-public-api-access-ai-scrapers)
- heise (2026-10-01) confirms the 2026-11-13 date and says readers using Feedly, Inoreader or NetNewsWire get no replacement. It describes the announcement as made "rather incidentally" in r/modnews. — [heise](https://www.heise.de/en/news/Reddit-to-shut-down-RSS-feeds-and-public-API-11473400.html)
- An unattributed search snippet, dated before the shutdown, said that on November 3 Reddit returned 403 to all logged-out JSON requests from one server while allowing about one RSS request a minute. [VENDOR/unclear] — surfaced via search; see [bigideasdb RSS page](https://bigideasdb.com/reddit-rss-feeds-ending)
- reddit-mcp-buddy's anonymous mode uses Reddit's public RSS feeds when available, so this project depends on RSS. — summary of [mcp.so listing](https://mcp.so/server/reddit-mcp-buddy) and [glama.ai](https://glama.ai/mcp/servers/i75lzw2wl2)

### Inferences
- Any keyless tool that falls back to `/r/<sub>/.rss` (reddit-mcp-buddy, for example) should be assumed broken, or at best unsupported and likely to be blocked at any time, after 2026-11-13.

### Gaps
- I found no post-2026-11-13 test showing whether `.rss` URLs now return 403 or 404, or still work for logged-in or residential users. This needs a live test.

## Anonymous `.json` endpoint blocking (HTTP 403 "blocked by network security")

### Takeaway
Reddit announced the shutdown of **unauthenticated `.json` endpoints** in r/modnews around 2026-05-28. Logged-out `.json` requests have returned 403 since late May or early June 2026, while logged-in and OAuth access were stated to be unaffected. The "blocked by network security" page itself is older: Reddit has shown it for IP-reputation blocks, including whole network blocks, since at least March 2025. On scope, residential IPs seem to fare better than datacenter, cloud and VPN IPs, but by policy anonymous `.json` is closed for everyone. **Most details here come from vendor blogs.**

### Cited Findings
- r/modnews post "Protecting communities from scrapers and platform abuse", 2026-05-28 (https://www.reddit.com/r/modnews/comments/1tq9vxo/). Reddit's quoted wording: "shutting down unauthenticated `.json` endpoints", which "can be used to scrape Reddit without accountability". Logged-in and OAuth access are not affected, and 403s began "within days". [VENDOR], cross-posted from crawlora.net, a commercial Reddit API. — [dev.to / Crawlora](https://dev.to/tonywangca/why-reddit-blocked-unauthenticated-json-in-2026-and-how-to-still-get-reddit-data-58b9)
- THINKPOL (2026-07-05, a [VENDOR]) gives the same rationale quote and says the shutdown was announced "late May 2026". It adds that Rule 8 was updated to cover automated abuse, including API misuse. — [THINKPOL](https://think-pol.com/blogs/reddit-is-closing)
- PPC Land [NEWS] dates the Rule 8 clarification and the `.json` shutdown to "around June 2026", with logged-in access unaffected. — [PPC Land](https://ppc.land/reddit-to-halt-public-data-api-access-in-march-2027-as-14-000-apps-register/)
- **Conflict:** one vendor blog says the block took effect 2026-05-30 without a formal announcement, which contradicts the r/modnews post cited by others. — summarized from [bigideasdb](https://bigideasdb.com/reddit-json-403-forbidden) and [redditapis.com](https://www.redditapis.com/blogs/reddit-json-endpoint-dead-2026)
- **Scope (IP type):**
  - Datacenter and cloud IPs are "heavily flagged"; a request may work from a residential browser but 403 from a server. [VENDOR] — [dev.to / Crawlora](https://dev.to/tonywangca/why-reddit-blocked-unauthenticated-json-in-2026-and-how-to-still-get-reddit-data-58b9)
  - Another project's docs say Reddit blocks unauthenticated requests from datacenter, cloud host, VPN and flagged IP ranges with an HTTP 403 block page. Seen via search snippet. — [contextbolt Reddit MCP guide](https://contextbolt.com/blog/reddit-mcp/)
- **The block page predates 2026 and is not specific to `.json`:**
  - Firefox users got "blocked by network security" on normal reddit.com pages in 2025. — [Mozilla Bugzilla 1983289](https://bugzilla.mozilla.org/show_bug.cgi?id=1983289)
  - Network operators reported whole IP blocks being blocked in March 2025. — [NANOG thread, Mar 2025](https://seclists.org/nanog/2025/Mar/190)
  - A security vendor KB documents Reddit 403s for proxied traffic. — [Skyhigh Security KB](https://success.skyhighsecurity.com/Skyhigh_Secure_Web_Gateway_(Cloud)/Troubleshooting_Connectivity_Issues/Troubleshoot_Reddit_Access_(403_Response))
- An MCP-breakage headline ("Reddit Blocks Anon API Access, Breaking Claude MCP") exists, but the page returned 403 and could not be read. — [AI Weekly](https://aiweekly.co/node/2176)
- A community Claude Code skill reports that arriving at Reddit via a DuckDuckGo redirect sets a session cookie that unlocks `.json` in a browser. This is unverified and likely against stated policy. — [tessl reddit-fetch skill](https://tessl.io/registry/skills/github/ykdojo/claude-code-tips/reddit-fetch)
- **Old Reddit:** on 2026-06-30 Reddit announced that Old Reddit requires login. In coming months, logged-in Old Reddit will be limited to users active on it in the prior six months, with moderators exempt. — [THINKPOL](https://think-pol.com/blogs/reddit-is-closing); [Decrypt](https://decrypt.co/379892/reddit-killing-rss-feeds-public-api-access-ai-scrapers); [PPC Land](https://ppc.land/reddit-to-halt-public-data-api-access-in-march-2027-as-14-000-apps-register/) (TechCrunch corrected the window from 90 days to six months)

### Inferences
- The old fallbacks (`old.reddit.com` HTML scraping and `.json` from a home IP) are now closed by policy for logged-out users. Any residual success from residential IPs is enforcement lag, not permission.
- Using a logged-in session cookie in a tool would be "authenticated" access. It would likely still fall under the User Agreement's rules on automated collection (see Gaps) and the bot/App-label policy.

### Gaps
- I could not read Reddit's 2026-05-28 r/modnews post directly, so the exact date and wording come from vendors.
- I found no official statement on residential vs datacenter treatment. All scope claims are vendor or anecdotal.

## User Agreement, Developer Terms, Public Content Policy: scraping, unauthenticated access, third-party archives; enforcement against archives

### Takeaway
I could not fetch any Reddit policy text directly; redditinc.com, reddithelp and archive.org were all blocked. Confirmed enforcement focuses on commercial scrapers and AI firms: lawsuits against Anthropic, Perplexity, SerpApi, Oxylabs and AWMProxy. Against archives, the known history is Pushshift losing public access in May 2023. Reddit also reportedly moved against Arctic Shift's public dumps in July 2026 (vendor claim). Arctic Shift is still up but unstable; PullPush is unreliable and frozen.

### Cited Findings
- Reddit sued SerpApi, Oxylabs, AWMProxy and Perplexity on 2025-10-22. The Anthropic case was remanded to state court on 2026-03-28. — [PPC Land](https://ppc.land/reddit-to-halt-public-data-api-access-in-march-2027-as-14-000-apps-register/)
- Case numbers: CGC-25-625892 (Anthropic) and 1:25-cv-08736 (Perplexity). Reddit excluded the Wayback Machine in 2025. — [heise](https://www.heise.de/en/news/Reddit-to-shut-down-RSS-feeds-and-public-API-11473400.html)
- In July 2024 Reddit changed robots.txt so that Google is the only major search engine indexing recent content. — [PPC Land](https://ppc.land/reddit-to-halt-public-data-api-access-in-march-2027-as-14-000-apps-register/)
- Reddit licenses data to Google (about $60M a year, Feb 2024) and OpenAI (May 2024). — [Decrypt](https://decrypt.co/379892/reddit-killing-rss-feeds-public-api-access-ai-scrapers); [PPC Land](https://ppc.land/reddit-to-halt-public-data-api-access-in-march-2027-as-14-000-apps-register/)
- **Pushshift:** lost public access in May 2023 and is now limited to approved moderators. **PullPush**, the community successor, "runs on a frozen dataset with tight rate limits". [VENDOR] — [THINKPOL, 2026-07-05](https://think-pol.com/blogs/reddit-is-closing)
- **PullPush status:** one source says ingestion stopped in May 2025; another reports HTTP 526 on 2026-11-07; a third lists it as "Unstable". [VENDOR], and the sources conflict. — summarized from [THINKPOL tools tested (Nov 2026)](https://think-pol.com/blogs/reddit-deleted-content-tools-tested), [chatterapi](https://chatterapi.com/blog/see-deleted-reddit-comments), [THINKPOL status](https://think-pol.com/blogs/reddit-archive-tools-status)
- **Arctic Shift status:** the API flapped on 2026-11-13 and 2026-11-16, and showed HTTP 200 at 2026-11-16 19:07 UTC. [VENDOR] — [THINKPOL status](https://think-pol.com/blogs/reddit-archive-tools-status)
  - A vendor claims Reddit began moving against Arctic Shift's public bulk dumps in July 2026, and that dumps lag 4 to 6 weeks. Unverified. — [redditapis.com](https://www.redditapis.com/blogs/reddit-archive-search-2026)
  - An Arctic Shift user said in Oct 2026 that it "still works, but it won't for long". The GitHub issue expects it to break after the API closure because it ingests via Reddit's API. — [GitHub issue #11](https://github.com/jordanallenlewis/reddit-research-mcp/issues/11)
- THINKPOL's claim that logging in makes collection "a breach of contract" (citing *hiQ v. LinkedIn*) is the vendor's interpretation, not a Reddit or court statement. — [THINKPOL](https://think-pol.com/blogs/reddit-is-closing)

### Inferences
- Reading from a third-party archive (Arctic Shift or PullPush) does not touch Reddit's servers, so Reddit's User Agreement does not bind the reader directly. The archive's own ingestion is what Reddit polices. Practically, the risk for a personal user is availability (the archive breaking or being shut down), not direct enforcement. This is my inference, not legal advice; no source states it.
- Arctic Shift is the most viable keyless source today but should be treated as at risk once the API closes in March 2027.

### Gaps
- **The exact User Agreement, Developer Terms, Data API Terms and Public Content Policy text was not retrievable.** My recollection, unverified in this session, is that the User Agreement (effective about 2024) forbids accessing, searching or collecting data "by any means (automated or otherwise)" except as its terms or a separate agreement allow, and only conditionally permits crawling per robots.txt. The 2024 Public Content Policy reportedly requires agreements for commercial and AI-training use and honouring deletions. Verify against redditinc.com/policies before relying on this.
- I found no Reddit statement specifically about individuals *using* third-party archives.
- I found no primary confirmation of a takedown or legal action against Arctic Shift or PullPush.

## Free tier: non-commercial use, 100 QPM, and what counts as commercial (incl. AI/LLM)

### Takeaway
The free tier has been 100 queries per minute per OAuth client ID, averaged over 10 minutes, since 2023-07-01, and is meant for non-commercial use (personal scripts, mod tools, accessibility, non-commercial academic research). Unauthenticated access was 10 QPM and is now effectively 0. The free tier only exists for already-approved apps and ends in March 2027. AI/LLM use of Reddit data is treated as needing a commercial contract.

### Cited Findings
- As of 2023-07-01, the free tier allows 100 QPM per OAuth client ID with OAuth and 10 QPM without it. — [zuplo guide](https://zuplo.com/blog/2024/10/01/reddit-api-guide), citing [Reddit's 2023 r/redditdev announcement (mirror)](https://reddit.rtrace.io/r/redditdev/comments/13wsiks/api_update_enterprise_level_tier_for_large_scale/jmr7eu0/?context=3)
- The limit is averaged over a 10-minute window. Personal scripts and bots, mod tools, accessibility apps and non-commercial academic research stay free; commercial and high-volume use needs an agreement. — [zuplo guide](https://zuplo.com/blog/2024/10/01/reddit-api-guide) (secondary)
- AI providers that accessed Reddit content via the API will need a commercial contract. — [heise](https://www.heise.de/en/news/Reddit-to-shut-down-RSS-feeds-and-public-API-11473400.html)
- A vendor (Data365, Nov 2026) repeats the dates: self-service ended 2025-11-11, new free access requests closed 2026-10-31, access ends March 2027. — [Data365](https://data365.co/blog/reddit-api-pricing)
- There is a vendor explainer on "what counts as commercial" for AI use, not read in full. — [redditapis.com commercial use](https://www.redditapis.com/blogs/reddit-api-commercial-use-licensing-explained-2026)

### Inferences
- A personal, non-commercial tool that passes Reddit content to an LLM such as Claude is a grey area. Reddit's AI licensing posture and the heise report suggest Reddit views LLM ingestion as commercial-contract territory, but I found no primary text saying personal LLM-assisted reading is banned.
- For a *new* keyless tool, the free tier is not reachable at all, because new requests closed on 2026-10-31.

### Gaps
- I could not read the current Data API Terms or Developer Terms to confirm their exact non-commercial and AI-training clauses.
- I found no official 2026 restatement of the 100 QPM figure. Whether it still applies to registered apps through March 2027 is unconfirmed.
