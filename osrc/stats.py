# -*- coding: utf-8 -*-

import os
import json
import flask
import operator
from math import sqrt
from collections import defaultdict

from . import github
from .models import User, Repo
from .redis import get_pipeline, get_connection, format_key

__all__ = ["user_stats", "repo_stats"]


def load_resource(
    filename,
    base=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
):
    return open(os.path.join(base, filename), "r")


def user_stats(username, tz_offset=True, max_connected=5, max_users=50):
    user = github.get_user(username)
    if user is None or not user.active:
        return flask.abort(404)

    #
    # REPOS:
    #
    conn = get_connection()
    repos = conn.zrevrange(format_key("u:{0}:r".format(user.id)), 0, 4,
                           withscores=True)
    repo_counts = []
    languages = defaultdict(int)
    for repo_id, count in repos:
        r = github.get_repo(id=int(repo_id))
        repo_counts.append((r, int(count)))
        if r.language is None:
            continue
        languages[r.language] += int(count)

    #
    # FRIENDS:
    #
    with load_resource("graph_user_user.lua") as script:
        get_users = get_connection().register_script(script.read())
    social = get_users(keys=["{0}".format(user.id).encode("ascii")],
                       args=[flask.current_app.config["REDIS_PREFIX"]])
    friends = []
    if len(social):
        ids = map(int, social[::2])
        friends = list(zip(User.query.filter(User.id.in_(ids)).all(),
                           map(int, social[1::2])))

    #
    # SIMILAR REPOS:
    #
    with load_resource("graph_user_repo.lua") as script:
        get_repos = get_connection().register_script(script.read())
    repo_scores = get_repos(keys=["{0}".format(user.id).encode("ascii")],
                            args=[flask.current_app.config["REDIS_PREFIX"]])
    repo_recs = []
    if len(repo_scores):
        ids = map(int, repo_scores[::2])
        repo_recs = list(zip(Repo.query.filter(Repo.id.in_(ids)).all(),
                             map(int, repo_scores[1::2])))

    #
    # SCHEDULE:
    #
    with get_pipeline() as pipe:
        pipe.zrevrange(format_key("u:{0}:e".format(user.id)), 0, 4,
                       withscores=True)
        keys = [(k.decode("ascii"), c) for k, c in pipe.execute()[0]]
        for k, _ in keys:
            key = format_key("u:{0}:e:{1}".format(user.id, k))
            pipe.hgetall(key)
        schedule = dict(zip((k for k, _ in keys), pipe.execute()))
    total_hist = dict((k, c) for k, c in keys)
    week_hist = defaultdict(lambda: list([0 for _ in range(7)]))
    day_hist = defaultdict(lambda: list([0 for _ in range(24)]))
    for t, vals in schedule.items():
        for day, counts in vals.items():
            counts = list(map(int, counts.decode("ascii").split(",")))
            sm = sum(counts)
            total_hist[t] += sm
            week_hist[t][int(day)] += sm
            for i, c in enumerate(counts):
                day_hist[t][i] += c

    # Correct for the timezone.
    if tz_offset and user.timezone:
        for t, v in day_hist.items():
            day_hist[t] = roll(v, user.timezone)

    #
    # PROSE DESCRIPTIONS:
    #
    h = [0 for _ in range(7)]
    for v in week_hist.values():
        for i, c in enumerate(v):
            h[i] += c
    descriptions = None
    norm = sqrt(sum([v * v for v in h]))
    if norm > 0.0:
        # A description of the most active day.
        with load_resource("days.json") as f:
            days = json.load(f)
        h = [_ / norm for _ in h]
        best = -1.0
        for d in days:
            vector = d["vector"]
            norm = 1.0 / sqrt(sum([v * v for v in vector]))
            dot = sum([(v*norm-w) ** 2 for v, w in zip(vector, h)])
            if best < 0 or dot < best:
                best = dot
                day_desc = d["name"]

        # A description of the most active time.
        with load_resource("times.json") as f:
            time_desc = json.load(f)
        h = [0 for _ in range(24)]
        for v in day_hist.values():
            for i, c in enumerate(v):
                h[i] += c
        time_desc = time_desc[sorted(zip(h, range(24)))[-1][1]]

        # Choose an adjective deterministically.
        with load_resource("adjectives.json") as f:
            adjs = json.load(f)
        lang = "coder"
        if len(languages):
            with load_resource("languages.json") as f:
                langs = json.load(f)
            l = sorted(languages.items(), key=operator.itemgetter(1))[-1]
            lang = langs.get(l[0], l[0] + " coder")

        # Describe the most common event type.
        with load_resource("event_actions.json") as f:
            acts = json.load(f)
        a = sorted(total_hist.items(), key=operator.itemgetter(1))[-1]
        action = acts.get(a[0], "pushing code")

        # Combine the descriptions.
        descriptions = dict(
            work_habits="{0} who works best {1}".format(day_desc, time_desc),
            language="{0} {1} who excels at {2}".format(
                adjs[abs(hash(user.login)) % len(adjs)], lang, action,
            ),
        )

    # Build the results dictionary.
    return dict(
        user.basic_dict(),
        descriptions=descriptions,
        events=[{"type": t, "count": c} for t, c in sorted(
            total_hist.items(), reverse=True, key=operator.itemgetter(1))],
        week=dict(week_hist),
        day=dict(day_hist),
        languages=[{"language": l, "count": c}
                   for l, c in sorted(languages.items(), reverse=True,
                                      key=operator.itemgetter(1))],
        repos=[dict(r.short_dict(), count=c) for r, c in repo_counts],
        friends=[dict(u.short_dict(), weight=c) for u, c in friends],
        repo_recs=[dict(r.short_dict(), weight=c) for r, c in repo_recs],
    )


def repo_stats(username, reponame):
    repo = github.get_repo("{0}/{1}".format(username, reponame))
    if repo is None or not repo.active or not repo.owner.active:
        return flask.abort(404)

    #
    # CONTRIBUTORS:
    #
    user_counts = []
    conn = get_connection()
    users = conn.zrevrange(format_key("r:{0}:u".format(repo.id)), 0, 4,
                           withscores=True)
    if len(users):
        ids, counts = zip(*(map(lambda u: map(int, u), users)))
        user_counts = list(zip(User.query.filter(User.id.in_(ids)).all(),
                           counts))

    #
    # SIMILAR REPOS:
    #
    repo_recs = []
    with load_resource("graph_repo_repo.lua") as script:
        get_repos = get_connection().register_script(script.read())
    social = get_repos(keys=["{0}".format(repo.id).encode("ascii")],
                       args=[flask.current_app.config["REDIS_PREFIX"]])
    if len(social):
        ids = map(int, social[::2])
        repo_recs = list(zip(Repo.query.filter(Repo.id.in_(ids)).all(),
                             map(int, social[1::2])))

    # Build the results dictionary.
    return dict(
        repo.basic_dict(),
        owner=None if repo.owner is None else repo.owner.basic_dict(),
        contributors=[dict(u.short_dict(), count=c) for u, c in user_counts],
        related_repos=[dict(r.short_dict(), weight=c) for r, c in repo_recs],
    )


def roll(x, shift):
    n = len(x)
    if n == 0:
        return x
    shift %= n
    s1 = slice(shift, n)
    s2 = slice(0, shift)
    return x[s1] + x[s2]
