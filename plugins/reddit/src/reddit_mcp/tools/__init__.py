"""Tool modules. Each has `register(mcp, ctx)`; `reddit_mcp.server` calls them all.

- status.py    Session 1: archive_status
- posts.py     Session 2: list_posts, search_posts, deep_search, get_posts
- comments.py  Session 3: get_thread, expand_comments, get_comment_context, search_comments
- discovery.py Session 4: find_subreddits, subreddit_info, read_wiki, get_user,
                          resolve_share_link, trending_posts, count_mentions
"""

from . import comments, discovery, posts, status

MODULES = (status, posts, comments, discovery)
