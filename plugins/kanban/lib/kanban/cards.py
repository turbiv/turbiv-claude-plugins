"""Merge Claude's decisions into the cards, by the field-ownership rules.

Claude decides which session belongs to which card and writes the summary,
the next step and one log line per session. This module does the rest:
ids, dates, lists, status rules, limits, and the record of synced sessions.
The rules are in resources/card-schema.md.
"""
import json
import random
import re
from datetime import datetime, timedelta, timezone

from .transcript import cut

TITLE_MAX, SUMMARY_MAX, NEXT_MAX, LOG_MAX = 80, 600, 200, 240
SUMMARY_BULLETS, BULLET_MAX = 4, 120   # `summary` is a few short bullets, one per line
LIST_MAX = 20                 # entries kept in `log` and in `sessions`
MAX_CARDS_PER_SESSION = 3
ARCHIVE_DAYS = 7              # done cards leave the Done column after a week
SYNCED_DAYS = 90
BATCH_MAX = 50                # ArtifactData takes at most 50 writes in one batch
NEW_STATUSES = ("idea", "todo", "doing", "done")
# The statuses sync may give a card that is already on the board, when it has newer work.
# "idea" only keeps an idea an idea; sync never turns other work back into one.
SYNC_STATUSES = ("idea", "todo", "doing", "done")
OPEN_AGAIN = ("done", "archived")
# "dropped" (Won't do) is only ever set by the owner, and sync never changes it:
# newer work on such a card is logged, but the card stays where the owner put it.
ID_CHARS = "abcdefghijkmnpqrstuvwxyz23456789"

SECRETS = [re.compile(p) for p in (
    r"gh[pousr]_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}", r"sk-[A-Za-z0-9_-]{20,}",
    r"AKIA[0-9A-Z]{16}", r"-----BEGIN [A-Z ]*PRIVATE KEY", r"xox[abprs]-[A-Za-z0-9-]{10,}",
    r"AIza[0-9A-Za-z_-]{30,}", r"eyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}",
)]


class Refused(Exception):
    """The decision cannot be applied. Nothing is written."""


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slug(title):
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-") or "card"
    return base + "-" + "".join(random.choice(ID_CHARS) for _ in range(4))


def _s(v):
    return v if isinstance(v, str) else ""


def _list(v):
    return v if isinstance(v, list) else []


_BULLET = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])\s+")


def summary_text(text):
    """The summary as it is stored: at most 4 bullets of at most 120 characters,
    one per line, each starting with "- ". A summary of one line with no bullet
    mark is a paragraph (cards from before the bullets) and is kept as it is."""
    text = _s(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return ""
    if len(lines) == 1 and not _BULLET.match(lines[0]):
        return cut(lines[0], SUMMARY_MAX)
    items = [cut(_BULLET.sub("", l, count=1).strip(), BULLET_MAX) for l in lines]
    return "\n".join("- " + i for i in [i for i in items if i][:SUMMARY_BULLETS])


def _check_secret(text, where):
    for pat in SECRETS:
        if pat.search(text):
            raise Refused("%s looks like it holds a secret (a token or a key). Take it out and run apply again." % where)


def _clean_links(links, where):
    out = []
    for link in _list(links):
        if not isinstance(link, dict):
            continue
        url, label = _s(link.get("url")).strip(), cut(_s(link.get("label")), 60)
        if not re.match(r"^https?://", url, re.I):
            continue
        _check_secret(url + " " + label, where + ".links")
        out.append({"label": label or url, "url": url})
    return out


def _union(old, new):
    out = [x for x in _list(old)]
    for x in new:
        if x and x not in out:
            out.append(x)
    return out


def _add_links(old, new):
    out = [l for l in _list(old) if isinstance(l, dict)]
    urls = {_s(l.get("url")) for l in out}
    for l in new:
        if l["url"] not in urls:
            out.append(l)
            urls.add(l["url"])
    return out


def merge(existing, decision, sessions, now, github=None):
    """The card after this sync.

    existing: the card as it is on the board, or None for a new card.
    decision: Claude's entry for the card (title, status, summary, next_step, links).
    sessions: [(session digest, log text)] for this card.
    github:   {repo name: url} from the digest.
    Returns the whole card. The caller sends only the changed fields for an
    existing card.
    """
    github = github or {}
    sessions = sorted(sessions, key=lambda p: p[0]["end"], reverse=True)
    new_end = sessions[0][0]["end"] if sessions else ""
    card = dict(existing) if existing else {}

    log = [{"date": s["end"], "text": cut(text, LOG_MAX), "session": s["id"]} for s, text in sessions if text.strip()]
    sess = [{"id": s["id"], "title": cut(s.get("title") or "", 80), "date": s["end"]} for s, _ in sessions]
    repos = [s["repo"] for s, _ in sessions if s.get("repo")]
    folders = [s["folder"] for s, _ in sessions if s.get("folder")]
    links = [{"label": "GitHub: " + r, "url": github[r]} for r in dict.fromkeys(repos) if github.get(r)]
    links += decision.get("_links", [])

    if existing is None:
        status = decision.get("status") if decision.get("status") in NEW_STATUSES else "doing"
        card.update({
            "title": cut(_s(decision.get("title")), TITLE_MAX), "status": status,
            "summary": summary_text(decision.get("summary")),
            "next_step": cut(_s(decision.get("next_step")), NEXT_MAX),
            "log": log[:LIST_MAX], "sessions": sess[:LIST_MAX],
            "repos": _union([], repos), "folders": _union([], folders), "links": _add_links([], links),
            "last_touched": new_end or iso(now),
            "created": min((s["start"] or s["end"] for s, _ in sessions), default=iso(now)),
            "status_changed_at": new_end or iso(now), "is_new": True, "notes": "",
        })
        return card

    # --- an existing card: the owner's fields stay as they are ---
    if _s(decision.get("summary")).strip():
        card["summary"] = summary_text(decision["summary"])
    if "next_step" in decision and isinstance(decision["next_step"], str):
        # A next step the owner wrote after this work is kept.
        if not (_s(existing.get("next_step_edited_at")) > new_end):
            card["next_step"] = cut(decision["next_step"], NEXT_MAX)
    # A status set by hand stays until there is newer work. Won't do stays always.
    if new_end and new_end > _s(existing.get("status_changed_at")) and existing.get("status") != "dropped":
        status = existing.get("status")
        want = decision.get("status")
        if want not in SYNC_STATUSES or (want == "idea" and status != "idea"):
            # No status in the decision: newer work makes the card active.
            want = "doing" if status in ("idea", "todo") or status in OPEN_AGAIN else None
        if want and want != status:
            card["status"] = want
            card["status_changed_at"] = iso(now)
            if status in OPEN_AGAIN and want != "done" and log:
                log[0]["text"] = cut("Reopened: " + log[0]["text"], LOG_MAX)
    seen = {(e["session"], e["date"]) for e in log}
    old_log = [e for e in _list(existing.get("log")) if isinstance(e, dict)
               and (e.get("session"), e.get("date")) not in seen]
    card["log"] = sorted(log + old_log, key=lambda e: _s(e.get("date")), reverse=True)[:LIST_MAX]
    ids = {s["id"] for s in sess}
    old_sess = [s for s in _list(existing.get("sessions")) if isinstance(s, dict) and s.get("id") not in ids]
    card["sessions"] = sorted(sess + old_sess, key=lambda s: _s(s.get("date")), reverse=True)[:LIST_MAX]
    card["repos"] = _union(existing.get("repos"), repos)
    card["folders"] = _union(existing.get("folders"), folders)
    card["links"] = _add_links(existing.get("links"), links)
    if new_end > _s(existing.get("last_touched")):
        card["last_touched"] = new_end
    return card


def _resolve(sid, by_id):
    if sid in by_id:
        return sid
    if len(sid) >= 6:
        hits = [k for k in by_id if k.startswith(sid)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise Refused("session id %r fits more than one session: %s. Give more of the id." % (sid, ", ".join(hits)))
    raise Refused("session %r is not in the digest of this sync." % sid)


def load_db(data):
    """The saved board snapshot: ({card id: card}, board or None, synced sessions or None)."""
    cards = {}
    folder = data.db / "cards"
    if folder.is_dir():
        for f in sorted(folder.glob("*.json")):
            try:
                c = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(c, dict):
                cards[f.stem] = c
    board = data.read_json("db/meta/board.json", None)
    synced = data.read_json("db/meta/synced.json", None)
    sessions = synced.get("sessions") if isinstance(synced, dict) and isinstance(synced.get("sessions"), dict) else None
    return cards, (board if isinstance(board, dict) else None), sessions


def plan(data, decision, now):
    """Work out every write. Raises Refused; touches no file."""
    digest = data.read_json("work/digest.json", None)
    if not isinstance(digest, dict) or not isinstance(digest.get("sessions"), list):
        raise Refused("there is no digest. Run `kanban-tool collect` first.")
    if not isinstance(decision, dict):
        raise Refused("the decision must be a JSON object with `cards` and `skip`.")
    by_id = {s["id"]: s for s in digest["sessions"]}
    existing, board, synced = load_db(data)
    versions = decision.get("versions") if isinstance(decision.get("versions"), dict) else {}
    github = {r["name"]: r["github"] for r in digest.get("repos", []) if r.get("github")}
    machine = _s(digest.get("machine"))

    used = {}          # session id -> [card ids]
    skipped = set()
    for item in _list(decision.get("skip")):
        sid = item.get("id") if isinstance(item, dict) else item
        skipped.add(_resolve(_s(sid), by_id))

    # A session with no title is named after its first prompt, and a prompt can
    # hold a token. Such a title must not reach the board.
    for s in digest["sessions"]:
        if any(pat.search(_s(s.get("title"))) for pat in SECRETS):
            s["title"] = "(title hidden: it looked like a secret)"

    final, writes, taken, seen_ids = dict(existing), [], set(existing), set()
    for n, d in enumerate(_list(decision.get("cards"))):
        where = "cards[%d]" % n
        if not isinstance(d, dict):
            raise Refused("%s is not an object." % where)
        cid = d.get("id")
        old = None
        if cid is not None:
            if cid not in existing:
                raise Refused("%s: card %r is not on the board. Use \"id\": null to make a new card." % (where, cid))
            if cid in seen_ids:
                raise Refused("%s: card %r is in the decision twice. Put all its sessions in one entry." % (where, cid))
            seen_ids.add(cid)
            old = existing[cid]
        elif not _s(d.get("title")).strip():
            raise Refused("%s: a new card needs a title." % where)
        for field in ("title", "summary", "next_step"):
            _check_secret(_s(d.get(field)), "%s.%s" % (where, field))
        pairs = []
        for entry in _list(d.get("sessions")):
            if not isinstance(entry, dict):
                raise Refused("%s.sessions holds something that is not an object." % where)
            sid = _resolve(_s(entry.get("id")), by_id)
            _check_secret(_s(entry.get("log")), "%s.sessions[%s].log" % (where, sid[:8]))
            pairs.append((by_id[sid], _s(entry.get("log"))))
        if old is None and not pairs:
            raise Refused("%s: a new card needs at least one session." % where)
        d = dict(d, _links=_clean_links(d.get("links"), where))
        card = merge(old, d, pairs, now, github)
        if old is None:
            cid = slug(card["title"])
            while cid in taken:
                cid = slug(card["title"])
            taken.add(cid)
            writes.append({"op": "set", "collection": "cards", "doc_id": cid, "data": card})
        else:
            changed = {k: v for k, v in card.items() if old.get(k) != v}
            if changed:
                writes.append({"op": "update", "collection": "cards", "doc_id": cid, "data": changed})
        final[cid] = card
        for s, _ in pairs:
            used.setdefault(s["id"], [])
            if cid not in used[s["id"]]:
                used[s["id"]].append(cid)

    for sid, cids in used.items():
        if len(cids) > MAX_CARDS_PER_SESSION:
            raise Refused("session %s is on %d cards. The most is %d." % (sid, len(cids), MAX_CARDS_PER_SESSION))
    both = skipped & set(used)
    if both:
        raise Refused("these sessions are both used and skipped: %s." % ", ".join(sorted(both)))
    left = [sid for sid in by_id if sid not in used and sid not in skipped]
    if left:
        raise Refused("these sessions are in the digest but in no card and not in `skip`: %s. "
                      "Put each one on a card or in `skip` with a reason." % ", ".join(left))

    # Done cards leave the Done column after ARCHIVE_DAYS.
    limit = iso(now - timedelta(days=ARCHIVE_DAYS))
    touched = {w["doc_id"] for w in writes}
    for cid, c in existing.items():
        if cid not in touched and c.get("status") == "done" and _s(c.get("status_changed_at")) < limit:
            change = {"status": "archived", "status_changed_at": iso(now)}
            writes.append({"op": "update", "collection": "cards", "doc_id": cid, "data": change})
            final[cid] = dict(c, **change)

    # The record of synced sessions.
    record = dict(synced or {})
    for sid in list(used) + sorted(skipped):
        prev = record.get(sid) if isinstance(record.get(sid), dict) else {}
        record[sid] = {"cards": _union(prev.get("cards"), used.get(sid, [])), "end": by_id[sid]["end"], "machine": machine}
    keep_after = iso(now - timedelta(days=SYNCED_DAYS))
    record = {k: v for k, v in record.items() if isinstance(v, dict) and _s(v.get("end")) >= keep_after}
    meta = [{"op": "set", "collection": "meta", "doc_id": "synced", "data": {"sessions": record},
             "_exists": synced is not None}]
    if board is None:
        meta.append({"op": "set", "collection": "meta", "doc_id": "board", "data": {
            "title": "Kanban", "schema": 1, "stale_days": 14, "cold_days": 30, "last_sync": iso(now)}})
    else:
        meta.append({"op": "update", "collection": "meta", "doc_id": "board", "data": {"last_sync": iso(now)}})
    writes += meta  # last: they record the sync as done

    missing = []
    for w in writes:
        key = w["collection"] + "/" + w["doc_id"]
        exists = w.pop("_exists", w["op"] == "update")
        if exists:
            v = versions.get(key)
            if not isinstance(v, int) or isinstance(v, bool):
                missing.append(key)
            else:
                w["if_version"] = v
    if missing:
        raise Refused("`versions` has no number for: %s. Take each version from the ArtifactData list result "
                      "and run apply again." % ", ".join(missing))
    return {"writes": writes, "final": final, "used": used, "skipped": sorted(skipped)}


def apply(data, decision, now, out):
    """Check the decision and write the files for the ArtifactData batch.

    Returns 0, or 2 when the decision is refused (then nothing is written).
    """
    try:
        result = plan(data, decision, now)
    except Refused as e:
        out.write("REFUSED: %s\nNothing was written.\n" % e)
        return 2
    outdir = data.clear(data.work / "out")
    listed = []
    for w in result["writes"]:
        path = data.write_json("work/out/%s/%s.json" % (w["collection"], w["doc_id"]), w["data"])
        entry = {"op": w["op"], "collection": w["collection"], "doc_id": w["doc_id"], "file_path": str(path)}
        if "if_version" in w:
            entry["if_version"] = w["if_version"]
        listed.append(entry)
    batches = [listed[i:i + BATCH_MAX] for i in range(0, len(listed), BATCH_MAX)]
    data.write_json("work/batch.json", {"writes": listed, "batches": batches})
    data.write_json("work/final.json", {"cards": result["final"], "used": result["used"], "skipped": result["skipped"]})

    made = [w for w in result["writes"] if w["collection"] == "cards" and w["op"] == "set"]
    changed = [w for w in result["writes"] if w["collection"] == "cards" and w["op"] == "update"]
    out.write("OK. %d new cards, %d changed cards, %d sessions placed, %d skipped.\n"
              % (len(made), len(changed), len(result["used"]), len(result["skipped"])))
    for w in made:
        out.write("  new: %s  %s\n" % (w["doc_id"], w["data"].get("title", "")))
    for w in changed:
        note = " -> " + w["data"]["status"] if "status" in w["data"] else ""
        out.write("  changed: %s%s\n" % (w["doc_id"], note))
    out.write("\nNow call ArtifactData with action \"batch\", the board URL, and these writes"
              "%s. Then run `kanban-tool commit`.\n" % (" (one call per list, in this order)" if len(batches) > 1 else ""))
    for b in batches:
        out.write(json.dumps(b) + "\n")
    return 0
