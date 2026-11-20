# Reddit Official Data API: Read-Only Feature Set (reference target for a keyless Reddit MCP)

Source note: reddit.com/dev/api, reddit.com wikis and support.reddithelp.com could not be fetched (reddit.com/redditinc.com blocked for the tool; reddithelp returned HTTP 403; web.archive.org blocked). The main primary-equivalent source used is the GitHub repo `Pyprohly/reddit-api-doc-notes`. It holds (a) `endpoint-scrape/`, a verbatim scrape of the official reddit.com/dev/api HTML, one file per endpoint, and (b) `docs/api-reference/*.rst`, hand-tested notes on actual behaviour. The repo's last commits are dated 2023-01-25, 2023-04-05 and 2024-07-01, so the scrape reflects the official docs around 2023-2024. Abbreviations used below: SCRAPE = official doc text from the scrape; NOTES = the tested notes. Base URL for SCRAPE files: https://github.com/Pyprohly/reddit-api-doc-notes/tree/master/endpoint-scrape

## Search endpoint (`/search`, `/r/{sub}/search`): parameters, allowed values, query syntax

### Takeaway
`GET [/r/{sub}]/search` (OAuth scope `read`) is a listing that takes `q` (max 512 chars), `restrict_sr`, `sort` (relevance|hot|top|new|comments), `t` (hour|day|week|month|year|all), `type` (sr|link|user), `category`, `include_facets`, `sr_detail` and the common listing params. In practice only `type=link` works on this endpoint, `sr_detail` is ignored, and timestamp/cloudsearch queries stopped working on the main stack in 2017-2018. Query syntax supports field operators (title:, author:, selftext:, subreddit:, url:, site:, flair:, self:, nsfw:), AND/OR/NOT (also `+`, `|`, `-`), parentheses and a `*` prefix wildcard. Results are capped at about 1000 per query.

### Cited Findings
**Official parameter list (SCRAPE, `GET [/r/subreddit]/search`, scope `read`, "Search links page. This endpoint is a listing.")** — [SCRAPE search](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/search/GET_r_subreddit_search.txt)
- `after` / `before`: fullname of a thing.
- `category`: "a string no longer than 5 characters".
- `count`: "a positive integer (default: 0)".
- `include_facets`: boolean value.
- `limit`: "the maximum number of items desired (default: 25, maximum: 100)".
- `q`: "a string no longer than 512 characters".
- `restrict_sr`: boolean value.
- `show`: "(optional) the string `all`".
- `sort`: one of `relevance`, `hot`, `top`, `new`, `comments`.
- `sr_detail`: "(optional) expand subreddits".
- `t`: one of `hour`, `day`, `week`, `month`, `year`, `all`.
- `type`: "(optional) comma-delimited list of result types (`sr`, `link`, `user`)".
- The official doc does NOT list `include_over_18` or `syntax` for `/search`. NSFW filtering in search follows the logged-in user's "include NSFW search results" preference, per the NOTES on `search_reddit_names`. Treat `include_over_18` on `/search` as undocumented. — [SCRAPE search](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/search/GET_r_subreddit_search.txt); [NOTES subreddit.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/subreddit.rst)

**Tested behaviour (NOTES, miscellaneous.rst "Search reddit submissions and subreddits")** — [NOTES miscellaneous.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/miscellaneous.rst)
- Use `GET /search` to search all of Reddit. Use `GET /r/{subreddit}/search` with `restrict_sr: 1` to search within one subreddit.
- "The `sr_detail` parameter is not supported (despite the offical docs saying so)."
- If `q` is empty or missing, an empty listing is returned.
- `restrict_sr`: limits results to the URL's subreddit. It is ignored if there is no subreddit in the URL, and also ignored when `type` is not `link`. Default false.
- `type`: one of `link`, `sr`, `user`, default `link`. "The documentation says this parameter takes a comma-separated list, but this is no longer the case." If you send a comma list, one type wins in the order link > sr > user. `sr` gives the same results as `GET /subreddits/search`. `user` "an empty paginated listing structure is always returned", so use `GET /users/search` instead. "So basically, only `link` is useful."
- `t`: valid `all`, `hour`, `day`, `week`, `month`, `year`; default `all`.
- `sort`: `relevance`, `hot`, `top`, `new`, `comments`; default `relevance`.
- The endpoint can sometimes return the string `"{}"`, e.g. with `type: sr, limit: 1`.

**PRAW (current client library, docs v8.0.3)** — [PRAW Subreddit docs](https://praw.readthedocs.io/en/stable/code_overview/models/subreddit.html)
- `Subreddit.search(query, *, sort='relevance', syntax='lucene', time_filter='all')`.
- `sort` is "relevance", "hot", "top", "new" or "comments". `syntax` is "cloudsearch", "lucene" or "plain" (default lucene). `time_filter` is "all", "day", "hour", "month", "week" or "year".
- PRAW points to https://www.reddit.com/r/reddit.com/wiki/search/ for query syntax.
- Note: PRAW still sends a `syntax` param, but the official endpoint doc scrape no longer lists `syntax`.

**Query syntax (community reference gist; the official wiki page could not be fetched)** — [douira gist "Reddit search syntax"](https://gist.github.com/douira/c2d158f76d41b931787c17d23ea0bb58)
- Field operators:
  - `title:`, `author:`, `selftext:`.
  - `subreddit:` (alias `reddit:`).
  - `url:` and `site:` (domain).
  - `nsfw:` (alias `over18:`), values `1`/`yes` or `0`/`no`.
  - `self:` (alias `is_self:`), values `1`/`yes` or `0`/`no`.
  - `flair:` (alias `flair_text:`), plus `flair_css_class:`.
  - `fullname:`.
  - `text:` is the default field. It covers title, author, selftext and subreddit.
- Booleans: space or `+` = AND, `|` or `OR` = OR, `-` or `NOT` = NOT. Parentheses group terms, e.g. `(cats|dogs)+bed`.
- `*` gives prefix matching, e.g. `redd*`.
- Known limits:
  - "Search results are limited to 1000 results."
  - Terms are stemmed.
  - "Searching for phrases doesn't seem to work" (gist last active Aug 2021).
  - Words containing symbols are split.
  - `author:` fails for usernames that contain `-`, because the dash is read as NOT.
- Cloudsearch syntax: `&syntax=cloudsearch` enabled `timestamp:start..end` in Unix time and `(and ...)` prefix grouping.
- URL search: "prefix `url:` to the url and surround the url in quotation marks"; "Reddit redirects URL searches to the submit page of the URL." — [PRAW FAQ](https://praw.readthedocs.io/en/stable/getting_started/faq.html)
- Third-party guides agree on `selftext:`, `flair:`, `self:yes|no`, `nsfw:yes|no` and AND/OR. They also show quoting multi-word values, e.g. `selftext:"first time home buyer" subreddit:personalfinance`. — [HowToGeek](https://www.howtogeek.com/808156/how-to-search-reddit-more-effectively/); [Online Tech Tips](https://www.online-tech-tips.com/computer-tips/advanced-search-on-reddit-like-a-pro/)

**CHANGE: timestamp search removed (2017-2018)** — [r/changelog "Update to search API", 29 Jan 2018 (mirror)](https://redlib.hbubli.cc/r/changelog/comments/7tus5f/update_to_search_api); [r/help "epoch timestamp search no longer working", 3 Aug 2017 (mirror)](https://r.datuan.dev/r/help/comments/6rc3i1/epoch_timestamp_search_no_longer_working); [timesearch README](https://git.voussoir.net/voussoir/timesearch/raw/commit/0ef423d780965da166e0b3cb1536ee7913dcecb9/README.md)
- Jan 2018: Reddit ran two search stacks, selectable with `?force_search_stack=fusion|cloudsearch`. Exact timestamp searches were not supported on the new "fusion" stack.
- Aug 2017: users reported timestamp search failing.
- The timesearch tool states "Reddit has removed the timestamp search feature".

### Inferences
- A keyless mirror should expose `q`, `subreddit` (implies restrict_sr), `sort` (5 values), `t` (6 values), `limit`/`after`, and `type` link|sr. Date-range filtering (`after`/`before` epoch) is a feature the official API LOST in 2018. An archive backend can add it as a superset.
- Phrase search quoting is unreliable on Reddit itself (per the 2021 gist). An archive full-text engine with real phrase support would be a strict improvement.

### Gaps
- Could not fetch the official https://www.reddit.com/wiki/search page (blocked), so the exact current operator list is from a 2021 community gist and secondary guides. I found no official 2025-2026 confirmation that `site:`, `url:` and `flair:` still behave identically.
- Allowed values for `category` and the shape of `include_facets` output are undocumented.
- Whether `syntax=lucene|plain|cloudsearch` is still honoured in 2026 is unverified.

## Listing endpoints: hot, new, rising, top, controversial, best; `t` param; pagination and the 1000 cap

### Takeaway
All listings share `after`, `before`, `count`, `limit` (default 25, max 100), `show=all` and `sr_detail`. Only `top` and `controversial` take `t` (hour|day|week|month|year|all, default all). `hot` adds `g` (geo filter, default GLOBAL). `best` is frontpage-only. Listings stop at about 1000 items. You page by passing the response's `after` fullname until it is `null`.

### Cited Findings
- `GET [/r/subreddit]/hot` (scope `read`) takes the base params plus `g`. `g` is one of GLOBAL, US, AR, AU, BG, CA, CL, CO, HR, CZ, FI, FR, DE, GR, HU, IS, IN, IE, IT, JP, MY, MX, NZ, PH, PL, PT, PR, RO, RS, SG, ES, SE, TW, TH, TR, GB, or a US state code `US_XX` (e.g. US_CA, US_NY, US_TX). — [SCRAPE hot](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/listings/GET_r_subreddit_hot.txt); default `GLOBAL` per [NOTES listings.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/listings.rst)
- `GET [/r/subreddit]/new` and `GET [/r/subreddit]/rising` take only the base params: after, before, count, limit (default 25, max 100), show, sr_detail. — [SCRAPE new](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/listings/GET_r_subreddit_new.txt); [SCRAPE rising](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/listings/GET_r_subreddit_rising.txt)
- `GET [/r/subreddit]/{sort}` covers `/top` and `/controversial`. Both take `t` (one of `hour`, `day`, `week`, `month`, `year`, `all`) plus the base params. — [SCRAPE sort](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/listings/GET_r_subreddit_sort.txt). Default `t=all` — [NOTES listings.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/listings.rst)
- `GET /best` takes the base params. — [SCRAPE best](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/listings/GET_best.txt)
- NOTES list `/best` at the frontpage and also `/r/{subreddit}/best`. Further listing paths:
  - `/gilded` and `/r/{sub}/gilded`.
  - `/comments` and `/r/{sub}/comments`, the newest-comments stream.
  - The frontpage `/` is the subscribed feed. With no user context, Reddit picks the subreddits. — [NOTES listings.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/listings.rst)
- `GET [/r/subreddit]/random` is "The Serendipity button". It redirects to a random post. — [SCRAPE random](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/listings/GET_r_subreddit_random.txt)
- `/comments` (newest comments) does not support `sr_detail`. Comment items there carry extra fields: `link_title`, `link_author`, `link_url`, `link_permalink`, `over_18`, `quarantine`, and `num_comments` (sometimes absent). — [NOTES listings.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/listings.rst)
- Other read listings and lookups:
  - `GET /duplicates/{article}` returns other submissions of the same URL. Params: `article`, `crossposts_only` (bool), `sort` (`num_comments` | `new`), `sr`, plus the base params. — [SCRAPE duplicates](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/listings/GET_duplicates_article.txt)
  - `GET /by_id/names` gets links by a comma-separated list of fullnames. — [SCRAPE by_id](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/listings/GET_by_id_names.txt)
  - `GET [/r/subreddit]/api/info` takes `id` (fullnames), `sr_name` or `url`. "Only Links, Comments, and Subreddits are allowed." — [SCRAPE info](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/links%20%26%20comments/GET_r_subreddit_api_info.txt)
  - `/api/info` limits (tested): up to 100 IDs, and more than 100 means all IDs are ignored. Up to 100 `sr_name` values, case-insensitive. Combined output is at most 200 items. Output order is random. IDs must be lowercase. The `url` param finds posts linking to a URL. — [NOTES submission.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/submission.rst)
- Pagination protocol (NOTES):
  - Pass `after`/`before` (only one) as a full ID36 cursor.
  - `limit` defaults to the user's preference, or 25 for client-credentials. "The maximum is 100. Larger numbers will be clamped."
  - "Do not depend on the number of results being fewer than the limit value to know whether your listing has reached the end. Use the `null` value of `after` instead."
  - `count` is the number of items already seen. It is also needed for `before` to be filled.
  - `show=all` disables filters such as "hide links I've voted on".
  - The `sr_detail` value is falsy if it starts with `0`, `F` or `f`.
  - — [NOTES listings.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/listings.rst)
- About 1000-item cap: "most of Reddit's listings contain a maximum of 1000 items, and are returned 100 at a time" (r/redditdev thread, Oct 2024, mirror). — [r/redditdev mirror](https://red.127.pp.ua/r/redditdev/comments/1gc46l8/submission_maximum_number_and_subredditnewlimit/ltrhahh/?context=3). Same for search: "Search results are limited to 1000 results." — [douira gist](https://gist.github.com/douira/c2d158f76d41b931787c17d23ea0bb58)
- `GET /api/trending_subreddits` is DEPRECATED: "This endpoint does not work". The documented path "always results in a HTTP 400 error". — [NOTES subreddit.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/subreddit.rst)

### Inferences
- Mirror target: sort ∈ {hot, new, rising, top, controversial} (+ best on frontpage). `t` only for top/controversial. Page size max 100, total depth about 1000. An archive can offer deeper history than 1000, which is a superset.
- `rising`, `hot` and `best` depend on live vote velocity and personalisation. A static archive can only approximate them, e.g. hot ≈ score decayed by age, and rising is likely not reproducible.
- `/gilded` listings are probably of little value after Reddit retired the old award system (2023). This is not verified here.

### Gaps
- No primary Reddit statement of the 1000 cap was fetchable. It is community-reported, but it is long-standing and consistent across sources.
- Did not verify the current status of `/gilded` or `/random` in 2026. `/random` has reportedly been changed or removed for some subreddits, but I have no source.

## Comments: `/comments/{id}` params and `/api/morechildren`

### Takeaway
`GET [/r/sub]/comments/{article}` (scope `read`) returns a 2-element array: [post listing, comment listing]. Key params are `comment`, `context` (0-8), `depth`, `limit`, `sort`, `threaded`, `truncate` (0-50), `showedits`, `showmore` and `sr_detail`. `sort` takes confidence|top|new|controversial|old|random|qa|live. `/api/morechildren` expands "load more comments" stubs, up to 100 IDs per call and one call at a time.

### Cited Findings
- Official params (SCRAPE) — [SCRAPE comments](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/listings/GET_r_subreddit_comments_article.txt):
  - `article` (ID36 of link).
  - `comment` (optional ID36, the focal comment).
  - `context`: "an integer between 0 and 8", the number of parents shown.
  - `depth` (optional int): "maximum depth of subtrees".
  - `limit` (optional int): "maximum number of comments to return".
  - `showedits`, `showmore` (bool).
  - `sort`: one of `confidence`, `top`, `new`, `controversial`, `old`, `random`, `qa`, `live`.
  - `sr_detail`.
  - `threaded` (bool).
  - `truncate`: "an integer between 0 and 50".
- Tested behaviour (NOTES) — [NOTES comment_tree.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/comment_tree.rst):
  - URL variants: `[/r/{sub}]/comments/{submission}` and `/comments/{submission}/_/{comment}`.
  - A wrong `{sub}` gives an empty listing.
  - The first listing holds the submission, with an extra `num_duplicates` field.
  - Comments carry `depth`, where top-level = 0.
  - `depth`: 0 is ignored, 1 means top-level only. "The maximum is 10, which is also the default."
  - `limit`: "The default seems to be 200, and the max value appears to be 500."
  - `context` above 8 is treated as 8.
  - Default `sort` is the user's preference, else `confidence` ('best').
- 'More' objects (NOTES):
  - "load more comments" has a `count` of total descendants and `children` IDs. Expand it with `/api/morechildren`.
  - "continue this thread" has id `_`, count 0 and empty children. Expand it by refetching `/comments/{article}` with `comment=<parent_id>`.
  - A deleted-without-trace focal comment returns an empty comment list, so clients should check for that.
  - — [NOTES comment_tree.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/comment_tree.rst)
- `GET /api/morechildren` (scope `read`) — [SCRAPE morechildren](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/links%20%26%20comments/GET_api_morechildren.txt):
  - "used to retrieve the additional comments represented by those stubs, up to 100 at a time."
  - Params: `api_type=json`, `children` (comma-delimited comment ID36s), `depth` (optional int), `id` (optional MoreChildren id), `limit_children` (bool, "only return the children requested"), `link_id` (fullname of the link), `sort` (same 8 values as above).
  - "NOTE: you may only make one request at a time to this API endpoint. Higher concurrency will result in an error being returned."
- morechildren tested behaviour (NOTES): it returns a FLAT array in pre-order DFS order, with `replies` always empty. Rebuild the tree from `parent_id`. HTTP 400 if there are too many `children`, 403 if `link_id` is missing or invalid. — [NOTES comment_tree.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/comment_tree.rst)
- Concurrent morechildren calls can yield 429. A User-Agent containing `curl` can also cause 429. — [RedditWarp rate-limit docs](https://redditwarp.readthedocs.io/en/latest/user-guide/rate-limits.html)

### Inferences
- Mirror target: get_post_comments(post_id, sort ∈ {confidence/best, top, new, controversial, old, qa}, limit, depth, comment_id+context). `random` and `live` are niche. `qa` needs OP/answer metadata that an archive may lack.
- An archive backend could return the full flat tree. That removes the need for a morechildren equivalent, though a "more" pagination tool is still useful for token budgets.

### Gaps
- No source found for whether `sort=random` or `live` are still supported in 2026.

## Subreddit discovery and metadata endpoints

### Takeaway
Discovery endpoints:
- `/subreddits/search` (q, sort relevance|activity, show_users, listing params).
- `/api/search_reddit_names` (query ≤50 chars, exact, include_over_18, include_unadvertisable).
- `/api/subreddit_autocomplete_v2` (query ≤25 chars, limit 1-10 default 5, include_over_18, include_profiles).
- `/subreddits/{popular|new|default|gold}`.

Metadata endpoints are `/r/{sub}/about`, `/about/rules`, `/sidebar`, `/sticky` and `/wiki/pages|{page}|revisions` (wiki needs scope `wikiread`).

### Cited Findings
- `GET /subreddits/search` (scope `read`), "Search subreddits by title and description". Params: `q`, `search_query_id` (uuid), `show_users` (bool), `sort` (`relevance` | `activity`), `typeahead_active`, plus the listing params. — [SCRAPE subreddits/search](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_subreddits_search.txt). Tested: it matches substrings of `display_name` and `public_description`. A missing `q` returns `"{}"`. `sr_detail` is not supported. `sort` and `show_users` "doesn't seem to do anything". — [NOTES subreddit.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/subreddit.rst)
- `GET /subreddits/{where}`, where is `popular`, `new`, `gold` or `default`. "popular sorts on the activity of the subreddit", "new sorts... based on their creation date, newest first". Listing params apply. — [SCRAPE subreddits/where](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_subreddits_where.txt). NOTES also list `/subreddits/premium`. — [NOTES listings.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/listings.rst)
- `GET /api/search_reddit_names` (GET or POST, scope `read`) lists subreddit names that begin with `query`. Params: `exact` (bool), `include_over_18` (bool), `include_unadvertisable` (bool), `query` ("up to 50 characters long"), `search_query_id`, `typeahead_active`. — [SCRAPE search_reddit_names](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_api_search_reddit_names.txt). Tested: it returns `{"names": [...]}` and the match is case-insensitive. `include_over_18` is ignored when there is a user context, where the NSFW-search preference is used instead, and defaults to true. `exact` with no match gives 404. Banned and private subreddits are included. — [NOTES subreddit.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/subreddit.rst)
- `POST /api/search_subreddits` takes the same params but returns partial subreddit objects. — [SCRAPE search_subreddits](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/POST_api_search_subreddits.txt)
- `GET /api/subreddit_autocomplete` takes `include_over_18`, `include_profiles` and `query` (≤25 chars). It "Uses typeahead endpoint... exact matches, typo correction, fuzzy matching". — [SCRAPE autocomplete](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_api_subreddit_autocomplete.txt)
- `GET /api/subreddit_autocomplete_v2` (scope `read`) takes `include_over_18`, `include_profiles` (bool), `limit` ("an integer between 1 and 10 (default: 5)"), `query` (≤25 chars), `search_query_id` and `typeahead_active`. — [SCRAPE autocomplete_v2](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_api_subreddit_autocomplete_v2.txt)
- DEPRECATED: `GET /api/recommend/sr/{srnames}` ("DEPRECATED: Return subreddits recommended for the given subreddit(s)", with params `omit` and `over_18`). — [SCRAPE recommend](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_api_recommend_sr_srnames.txt). NOTES also list an undocumented `GET /api/similar_subreddits`. — [NOTES subreddit.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/subreddit.rst)
- `GET /r/{sub}/about` (scope `read`): "subscriber count, description, and header image". — [SCRAPE about](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_r_subreddit_about.txt). Key fields:
  - `display_name`, `title` (≤100 chars).
  - `public_description`, `description` (markdown).
  - `subscribers`, `active_user_count` (`accounts_active` is deprecated).
  - `created_utc`, `over18`, `lang`.
  - `subreddit_type`: one of public, private, restricted, archived, employees_only, gold_only, gold_restricted, user.
  - `/about` errors for private or banned subreddits. `/api/info` returns them with many null values.
  - — [NOTES subreddit.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/subreddit.rst)
- `GET /r/{sub}/about/rules` (scope `read`) returns `{rules, site_rules, site_rules_flow}`. Each rule has:
  - `priority`.
  - `kind`: `all`, `link` or `comment`.
  - `description` (≤500 chars), `description_html`.
  - `short_name` (≤100 chars), `violation_reason`.
  - `created_utc`.
  - An unknown subreddit gives an empty listing. — [NOTES subreddit.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/subreddit.rst); [SCRAPE rules](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_r_subreddit_about_rules.txt)
- Other subreddit reads:
  - `GET [/r/sub]/sidebar` (read).
  - `GET [/r/sub]/sticky` with `num` (1-2, default 1). It redirects to a stickied post, or 404s.
  - `GET /r/{sub}/about/traffic` needs scope `modconfig`, so it is moderator-only. — [SCRAPE sidebar](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_r_subreddit_sidebar.txt); [SCRAPE sticky](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_r_subreddit_sticky.txt); [SCRAPE traffic](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_r_subreddit_about_traffic.txt)
  - `GET /r/{sub}/api/widgets` (scope `structuredstyles`, `progressive_images` bool). — [SCRAPE widgets](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/widgets/GET_r_subreddit_api_widgets.txt)
  - `GET /api/v1/collections/subreddit_collections?sr_fullname=` and `GET /api/v1/collections/collection?collection_id=&include_links=` (read). — [SCRAPE collections](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/collections/GET_api_v1_collections_subreddit_collections.txt)
  - `GET /r/{sub}/api/link_flair_v2` (scope `flair`) only returns flair if the user can set their own flair. — [SCRAPE link_flair_v2](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/flair/GET_r_subreddit_api_link_flair_v2.txt)
- Wiki (scope `wikiread`):
  - `GET [/r/sub]/wiki/pages` lists pages.
  - `GET [/r/sub]/wiki/{page}` takes `v` (revision ID, "show the wiki page as it was at that version") and `v2` ("If both v and v2 are given, show a diff").
  - `GET [/r/sub]/wiki/revisions` and `/wiki/revisions/{page}` are listings.
  - `GET [/r/sub]/wiki/discussions/{page}` is a listing.
  - — [SCRAPE wiki page](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/wiki/GET_r_subreddit_wiki_page.txt); [SCRAPE wiki pages](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/wiki/GET_r_subreddit_wiki_pages.txt); [SCRAPE revisions](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/wiki/GET_r_subreddit_wiki_revisions_page.txt)
  - Tested: `v2` "seems to have no effect in the JSON API". Errors are PAGE_NOT_FOUND 404, private 403 and banned 404. — [NOTES wiki.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/wiki.rst)
- Multireddits (read): `GET /api/multi/{multipath}` and `GET /api/multi/user/{username}`, both with `expand_srs` (bool). — [SCRAPE multi](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/multis/GET_api_multi_user_username.txt)

### Inferences
- Mirror target: search_subreddits(q), autocomplete(prefix, nsfw flag, limit≤10), subreddit_about, rules, wiki list/page. Popular/new subreddit lists need activity data that an archive can compute from post volume.
- Sidebar, widgets and live `active_user_count` are live-only data. An archive can at best snapshot them.

### Gaps
- `/api/subreddit_autocomplete_v2` response shape was not captured. It is believed to be a listing of subreddit (and profile, if `include_profiles`) objects, but this is unverified.

## User endpoints

### Takeaway
`/user/{name}/about` gives karma and account metadata. `/user/{name}/{overview|submitted|comments|gilded}` are public listings with `sort` (hot|new|top|controversial) and `t` (hour..all). upvoted, downvoted, hidden and saved are private. `/users/search` and `/users/popular|new` cover profile discovery. Trophies live at `/api/v1/user/{name}/trophies`.

### Cited Findings
- `GET /user/{username}/about` (scope `read`): "information about the user, including karma and gold status". — [SCRAPE user about](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/users/GET_user_username_about.txt). Fields:
  - `name`, `id` (no `t2_`), `created_utc`.
  - `link_karma`, `comment_karma`, `awardee_karma`, `awarder_karma`, `total_karma`.
  - `is_gold`, `is_mod`, `is_employee`, `verified`, `has_verified_email`, `icon_img`.
  - `is_suspended` (present only if suspended).
  - `subreddit` (profile sub-object, with `over_18`).
  - — [NOTES user.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/user.rst)
- `GET /user/{username}/{where}` (scope `history`), a listing. Where is overview, submitted, comments, upvoted, downvoted, hidden, saved or gilded. — [SCRAPE user where](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/users/GET_user_username_where.txt). Params:
  - `context` (2-10).
  - `show` (`given`).
  - `sort`: `hot`, `new`, `top`, `controversial`.
  - `t`: `hour`, `day`, `week`, `month`, `year`, `all`.
  - `type`: `links` or `comments`.
  - `username`, plus the listing params.
- Tested user-listing behaviour (NOTES) — [NOTES user.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/user.rst):
  - overview, submitted, comments and gilded are "Available publicly for any user".
  - upvoted and downvoted are public only if the user enabled public votes. hidden and saved are never public.
  - Default `sort` is `new` for overview and comments, `hot` for submitted.
  - `/comments` does not support `sr_detail`. `type` applies to saved.
  - Errors: 404 for an unknown user, 403 when there is no permission.
- `GET /api/v1/user/{username}/trophies` (read). — [SCRAPE trophies](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/users/GET_api_v1_user_username_trophies.txt)
- `GET /users/search` (read), "Search user profiles by title and description". Params: `q`, `sort` (relevance | activity), `search_query_id`, `typeahead_active`, plus the listing params. — [SCRAPE users/search](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_users_search.txt)
- `GET /users/{popular|new}`. — [SCRAPE users/where](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/subreddits/GET_users_where.txt)
- NOTES also list `GET /user/{user}/moderated_subreddits` (undocumented). — [NOTES user.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/user.rst)

### Inferences
- Mirror target: user_about (karma, created), user_posts and user_comments with sort ∈ {new, top, controversial, hot} and `t`. Karma totals are live-only, but an archive can compute activity counts.

### Gaps
- Behaviour of `/gilded` after the Sept 2023 awards overhaul is not verified.

## Response fields that matter

### Takeaway
Submission (t3) fields for research: `id`/`name` (t3_ fullname), `title`, `selftext`, `author`, `subreddit`, `subreddit_id`, `score` (= `ups`; `downs` is always 0), `upvote_ratio`, `num_comments` (an estimate), `created_utc`, `link_flair_text`, `link_flair_template_id`, `permalink` (no domain), `url`, `domain`, `is_self`, `over_18`, `spoiler`, `stickied`, `locked`, `archived`, `edited` (false or a timestamp), `distinguished`, `num_crossposts`, `crosspost_parent`, `removed_by_category`, `is_video`, `post_hint` and `subreddit_subscribers`.

### Cited Findings
- From the NOTES Submission schema — [NOTES submission.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/submission.rst):
  - Score and votes:
    - `score`: "The number of upvotes (minus downvotes). This attribute will work even if `hide_score` is `true`."
    - `ups`: "Same as `score`." `downs`: "Always `0`."
    - `upvote_ratio`: float.
    - `num_comments`: "should be treated as an estimation".
  - Time:
    - `created_utc`: Unix timestamp, always whole.
    - `created`: "Legacy. Same as `created_utc` but subtract 28800."
    - `edited`: `false` or a Unix timestamp.
  - Links, flair and media:
    - `permalink`: URL without the domain.
    - `url`: the link target, or the post's own URL for self posts.
    - `domain`: for text posts it is `self.<sub>`.
    - `link_flair_text` (string or null), `link_flair_template_id`, `link_flair_richtext`.
    - `post_hint`, `is_video`, `thumbnail`.
  - Status flags:
    - `stickied`, `over_18`, `spoiler`, `locked`, `archived`.
    - `is_self`: true for text and poll posts.
    - `distinguished`: `moderator`, `admin` or null.
  - Identity and crossposts:
    - `name` (t3_ fullname), `id`, `subreddit_id` (t5_).
    - `num_crossposts`, `crosspost_parent`.
    - `subreddit_subscribers`.
  - Removal:
    - `removed_by_category`: null if not removed. Use it rather than `removed` to detect removal.
    - `author`: may be `[removed]` or `[deleted]`.
- Comment listings add `depth`, and the `/comments` stream adds `link_title`, `link_permalink` and similar. — [NOTES comment_tree.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/comment_tree.rst); [NOTES listings.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/listings.rst)
- Fullname prefixes: t1 = comment, t2 = account, t3 = link, t5 = subreddit, as used throughout the NOTES. — [NOTES submission.rst](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/docs/api-reference/submission.rst)

### Inferences
- An archive snapshot captures `score`, `upvote_ratio` and `num_comments` at ingest time. A mirror should expose a "retrieved_at" field, because the official API returns live values.

### Gaps
- I did not capture a separate comment-object schema list (body, score, parent_id, link_id, is_submitter, controversiality). These are standard, but I did not verify them against a fetched source in this session.

## Rate limits, X-Ratelimit headers, User-Agent rules, access policy (as of Nov 2026)

### Takeaway
Free OAuth tier: 100 queries per minute per OAuth client ID, averaged over a 10-minute window. RedditWarp observes this as 996 requests per 600 s, or 600/600 s for app-only grants. The old 60/min wiki figure is pre-July-2023. Headers are `X-Ratelimit-Used`, `X-Ratelimit-Remaining` and `X-Ratelimit-Reset` (seconds, not a timestamp). User-Agent must be `<platform>:<app ID>:<version> (by /u/<username>)`. Since Nov 2025 (Responsible Builder Policy), new API access needs manual approval. Unauthenticated access has reportedly been blocked since 30 May 2026, but this is unverified.

### Cited Findings
- Archived official wiki (last edited 18 Dec 2015, repo archived 9 Nov 2017) — [reddit-archive/reddit wiki API](https://github.com/reddit-archive/reddit/wiki/API):
  - "Clients connecting via OAuth2 may make up to 60 requests per minute." This is SUPERSEDED.
  - Header definitions:
    - `X-Ratelimit-Used`: "Approximate number of requests used in this period".
    - `X-Ratelimit-Remaining`: "Approximate number of requests left to use".
    - `X-Ratelimit-Reset`: "Approximate number of seconds to end of period".
  - User-Agent format: `<platform>:<app ID>:<version string> (by /u/<reddit username>)`, e.g. `android:com.example.myredditapp:v1.2.3 (by /u/kemitche)`.
  - "NEVER lie about your user-agent". Spoofing browsers is banned. Default UAs like "Python/urllib" are heavily restricted.
  - "Requests for multiple resources at a time are always better than requests for single-resources in a loop."
- CHANGE (effective about 1 July 2023): free tier became 100 QPM per OAuth client ID, averaged over 10 minutes. Previously it was 60 QPM. This is reported by secondary sources citing Reddit's Data API Wiki. I could not fetch the primary page (reddithelp returned HTTP 403). — [data365 blog](https://data365.co/blog/reddit-api-limits); [r/redditdev "updated rate limits going into effect", 30 Jun 2023 (mirror, fetch failed)](https://lr.in.psf.lt/r/redditdev/comments/14nbw6g/updated_rate_limits_going_into_effect_over_the/k2cksjp/?context=3); [zuplo guide](https://zuplo.com/blog/2024/10/01/reddit-api-guide)
- Observed: global limit "996 requests per 600-second window", "600/600s" for application-only grants, "on a per client ID basis". `x-ratelimit-reset` is the number of seconds until the window resets. When over the limit, remaining stays 0 and used keeps rising. Endpoint-local limits give a `RATELIMIT` error. — [RedditWarp rate limits](https://redditwarp.readthedocs.io/en/latest/user-guide/rate-limits.html)
- Third-party 2026 figures (activepieces blog, 1 Nov 2026, citing ApixStar), labelled "As checked 1 Nov 2026":
  - OAuth: 100 req/min per client ID.
  - Unauthenticated: 10/min, but "have been blocked since 30 May 2026". The article's own FAQ calls this "unconfirmed".
  - Every access route requires approval. Tokens last 1 h.
  - — [activepieces](https://www.activepieces.com/blog/reddit-api-access-in-2026-how-to-get-started.md)
- CHANGE (11 Nov 2025): the "Responsible Builder Policy" closed self-service API access. "self-service access to Reddit's public data API will be closed". Developers, researchers and mods must request approval. Existing tokens were not revoked. Reddit aims for a 7-day turnaround, but users report slow reviews and rejections. — [r/redditdev announcement, 11 Nov 2025 (mirror)](https://r.datuan.dev/r/redditdev/comments/1oug31u/introducing_the_responsible_builder_policy_new/noc31sg)
- OAuth scopes relevant to read-only use, taken from the endpoint scrapes:
  - `read`: listings, search, comments, about, rules, info.
  - `history`: user listings.
  - `wikiread`: wiki.
  - `flair`, `structuredstyles` (widgets) and `modconfig` (traffic, moderator-only).
  - `GET /api/v1/scopes` describes the scopes. — [SCRAPE scopes](https://github.com/Pyprohly/reddit-api-doc-notes/blob/master/endpoint-scrape/misc/GET_api_v1_scopes.txt)

### Inferences
- Because new keys need approval and unauthenticated JSON is reportedly blocked, a "keyless" Reddit MCP in late 2026 practically has to rely on a third-party archive. This matches the project premise.
- The rate-limit model is a useful design target for polite client-side throttling: about 100/min, burst-tolerant over 10 min, and honouring the Remaining/Reset headers if a backend provides similar ones.

### Gaps
- Could not fetch the primary Reddit Data API Wiki (support.reddithelp.com returned HTTP 403), so the exact current wording of the 100 QPM / 10-minute rule and the unauthenticated limit is from secondary sources.
- The 30 May 2026 unauthenticated block is single-sourced (ApixStar via activepieces) and unverified.
- `raw_json=1` (which disables HTML-entity escaping in JSON) is widely used, but I found no fetched source confirming it this session.
