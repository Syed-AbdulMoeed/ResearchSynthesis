from collections import Counter, defaultdict
from datetime import date, timedelta

from psycopg import connect
from psycopg.rows import dict_row

from database import CONNECTION


def get_week_range(week_start=None):
    """ Turn any day (a date, an ISO string like "2026-10-28", or None for today)
    into that week's Monday and the next Monday: [start, end).
    "Week" always means the paper's own pub_date, never the day it was processed."""
    if week_start is None:
        day = date.today()
    elif isinstance(week_start, str):
        day = date.fromisoformat(week_start)
    else:
        day = week_start
    start = day - timedelta(days=day.weekday())      # weekday(): Monday = 0
    return start, start + timedelta(days=7)


def get_latest_week_start():
    """The Monday of the week of the NEWEST paper in the database.
    Used when no week is given, so the default is "the latest week that has data"
    instead of today's week (which is often still empty). Falls back to today if there are no papers."""
    with connect(CONNECTION) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(pub_date) FROM papers")
            latest = cur.fetchone()[0]
    return latest  # None if the table is empty -> get_week_range(None) then uses today


def get_week_meta(cur, start, end):
    """Numbers about the week as a whole (the 'denominator' for every technology)."""
    cur.execute("""SELECT COUNT(*) AS n FROM papers
                   WHERE pub_date >= %s AND pub_date < %s""", (start, end))
    papers_this_week = cur.fetchone()["n"]

    cur.execute("""SELECT category, COUNT(*) AS n FROM papers
                   WHERE pub_date >= %s AND pub_date < %s
                   GROUP BY category ORDER BY n DESC""", (start, end))
    categories = {r["category"]: r["n"] for r in cur.fetchall()}

    # How many different weeks the system has data for (up to the end of this week).
    # The LLM needs this so it does not call something a "trend" after 1-2 weeks of data.
    cur.execute("""SELECT COUNT(DISTINCT date_trunc('week', pub_date)) AS n FROM papers
                   WHERE pub_date < %s""", (end,))
    weeks_of_data = cur.fetchone()["n"]

    # Mentions the reviewer could not settle: this week's counts may be slightly low.
    cur.execute("""SELECT COUNT(*) AS n FROM unresolved_keywords u
                   JOIN papers p ON p.id = u.paper_id
                   WHERE p.pub_date >= %s AND p.pub_date < %s""", (start, end))
    unresolved = cur.fetchone()["n"]

    return {"papers_this_week": papers_this_week, "categories": categories,
            "weeks_of_data": weeks_of_data, "unresolved_keywords": unresolved}


def get_week_report(week_start=None, history_weeks=4, max_titles=3,
                    min_papers=2, max_repeated=40, max_singletons=100):
    """ Everything the trend LLM call needs, kept SMALL on purpose.

    Most technologies are mentioned in just ONE paper, so they only get a name, not a full record:
      - repeated: full records for technologies in >= `min_papers` papers this week
                  (is_new_this_week says whether the technology was also created this week).
                  Capped at `max_repeated`, biggest first.
      - new_single_mention: names of technologies created this week that only ONE paper mentioned.
      - counts: totals for everything, including what was left out by a cap or not listed.
    Use min_papers=1 to get a full record for every technology (large output!).
    """
    if week_start is None:
        week_start = get_latest_week_start()   # latest week with data, not today's week
    start, end = get_week_range(week_start)

    with connect(CONNECTION) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            meta = get_week_meta(cur, start, end)

            # Every alias row (technology, spelling, paper) from a paper published this week.
            cur.execute("""
                SELECT al.name, al.alias, al.paper_id, p.category, p.title
                FROM aliases al JOIN papers p ON p.id = al.paper_id
                WHERE p.pub_date >= %s AND p.pub_date < %s""", (start, end))
            week_rows = cur.fetchall()

            # Technologies created this week = their first paper is from this week.
            cur.execute("""
                SELECT t.name FROM technologies t JOIN papers p ON p.id = t.paper_id
                WHERE p.pub_date >= %s AND p.pub_date < %s""", (start, end))
            new_names = {r["name"] for r in cur.fetchall()}

            # Group this week's rows per technology (in Python, so it stays readable).
            # A paper can mention a technology under two spellings, so we count DISTINCT papers.
            papers = defaultdict(set)                     # name -> {paper_id}
            spellings = defaultdict(lambda: defaultdict(set))   # name -> alias -> {paper_id}
            cat_papers = defaultdict(lambda: defaultdict(set))  # name -> category -> {paper_id}
            titles = defaultdict(dict)                    # name -> {paper_id: title}
            for r in week_rows:
                papers[r["name"]].add(r["paper_id"])
                spellings[r["name"]][r["alias"]].add(r["paper_id"])
                cat_papers[r["name"]][r["category"]].add(r["paper_id"])
                titles[r["name"]][r["paper_id"]] = r["title"]

            # Split: repeated (full record) vs single mention (name only)
            n_papers = {n: len(p) for n, p in papers.items()}
            repeated_all = sorted((n for n, c in n_papers.items() if c >= min_papers),
                                  key=lambda n: (-n_papers[n], n))
            names = repeated_all[:max_repeated]
            new_single = sorted(n for n in new_names if n_papers.get(n, 0) < min_papers)
            other_single = sum(1 for n, c in n_papers.items() if c < min_papers and n not in new_names)

            first, totals, history = {}, {}, defaultdict(dict)
            if names:   # the heavy queries only run for the few technologies that need them
                # The technologies-table row for each one: its FIRST mention.
                cur.execute("""
                    SELECT t.name, t.paper_id, p.title, p.pub_date
                    FROM technologies t JOIN papers p ON p.id = t.paper_id
                    WHERE t.name = ANY(%s)""", (names,))
                first = {r["name"]: r for r in cur.fetchall()}

                # Total mentions UP TO THE END of this week (so looking at an old week
                # does not count papers that came later).
                cur.execute("""
                    SELECT al.name,
                           COUNT(DISTINCT al.paper_id) AS papers,
                           COUNT(DISTINCT al.alias)    AS spellings
                    FROM aliases al JOIN papers p ON p.id = al.paper_id
                    WHERE al.name = ANY(%s) AND p.pub_date < %s
                    GROUP BY al.name""", (names, end))
                totals = {r["name"]: r for r in cur.fetchall()}

                # Papers per week for the previous `history_weeks` weeks (the baseline).
                cur.execute("""
                    SELECT al.name, date_trunc('week', p.pub_date)::date AS wk,
                           COUNT(DISTINCT al.paper_id) AS n
                    FROM aliases al JOIN papers p ON p.id = al.paper_id
                    WHERE al.name = ANY(%s) AND p.pub_date >= %s AND p.pub_date < %s
                    GROUP BY al.name, wk""", (names, start - timedelta(weeks=history_weeks), start))
                for r in cur.fetchall():
                    history[r["name"]][r["wk"]] = r["n"]

    # Build one record per repeated technology.
    records = []
    for name in names:
        f = first[name]
        this_week = n_papers[name]
        records.append({
            "name": name,
            "is_new_this_week": name in new_names,
            "papers_this_week": this_week,
            "share_of_week_papers": round(this_week / meta["papers_this_week"], 3)
                                    if meta["papers_this_week"] else 0.0,
            # spellings used THIS week, each with how many papers used it
            "aliases_this_week": {a: len(p) for a, p in sorted(
                spellings[name].items(), key=lambda x: (-len(x[1]), x[0]))},
            # the technologies-table row (its first mention)
            "first_mention": {"paper_id": f["paper_id"], "title": f["title"],
                              "pub_date": f["pub_date"].isoformat()},
            # calendar weeks (Monday to Monday), so it lines up with prev_weeks:
            # first seen 13 days ago but in the week of 2 Mondays ago -> 2, not 1
            "weeks_since_first_seen": max(0, (start - (f["pub_date"] - timedelta(days=f["pub_date"].weekday()))).days // 7),
            "total_papers_to_date": totals[name]["papers"],
            "total_spellings_to_date": totals[name]["spellings"],
            # oldest -> newest, the last entry is the week right before this one
            "prev_weeks": [history[name].get(start - timedelta(weeks=k), 0)
                           for k in range(history_weeks, 0, -1)],
            "categories_this_week": dict(sorted(
                ((c, len(p)) for c, p in cat_papers[name].items()), key=lambda x: -x[1])),
            "example_titles": list(titles[name].values())[:max_titles],
        })

    return {
        "week_start": start.isoformat(), "week_end": end.isoformat(), "meta": meta,
        "counts": {"new_total": len(new_names),
                   "repeated_total": len(repeated_all), "repeated_shown": len(records),
                   "new_single_mention_total": len(new_single),
                   "new_single_mention_shown": min(len(new_single), max_singletons),
                   "other_single_mention": other_single},
        "repeated": records,
        "new_single_mention": new_single[:max_singletons],
    }


def report_to_json(report):
    """ The compact text to put in the LLM prompt: no indentation, no \\uXXXX escapes."""
    import json
    return json.dumps(report, separators=(",", ":"), ensure_ascii=False)


if __name__ == "__main__":
    text = report_to_json(get_week_report())
    print(text)
    print(f"\n[{len(text)} characters]")