#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["get_user_info", "get_social_stats", "get_usage_stats"]

import json
import flask
import requests
import numpy as np

from .index import get_neighbors
from .timezone import estimate_timezone
from .database import get_connection, get_pipeline, format_key

ghapi_url = "https://api.github.com/users/{username}"


def get_user_info(username):
    # Normalize the username.
    user = username.lower()

    # Get the cached information.
    pipe = get_pipeline()
    pipe.get(format_key("user:{0}:name".format(user)))
    pipe.get(format_key("user:{0}:etag".format(user)))
    pipe.get(format_key("user:{0}:gravatar".format(user)))
    pipe.get(format_key("user:{0}:tz".format(user)))
    pipe.exists(format_key("user:{0}:optout".format(user)))
    name, etag, gravatar, timezone, optout = pipe.execute()
    if optout:
        return None

    if name is not None:
        name = name.decode("utf-8")

    # Work out the authentication headers.
    auth = {}
    client_id = flask.current_app.config.get("GITHUB_ID", None)
    client_secret = flask.current_app.config.get("GITHUB_SECRET", None)
    if client_id is not None and client_secret is not None:
        auth["client_id"] = client_id
        auth["client_secret"] = client_secret

    # Perform a conditional fetch on the database.
    headers = {}
    if etag is not None:
        headers = {"If-None-Match": etag}

    r = requests.get(ghapi_url.format(username=username), params=auth,
                     headers=headers)
    code = r.status_code
    if code != 304 and code == requests.codes.ok:
        data = r.json()
        name = data.get("name") or data.get("login") or username
        etag = r.headers["ETag"]
        gravatar = data.get("gravatar_id", "none")
        location = data.get("location", None)
        if location is not None:
            tz = estimate_timezone(location)
            if tz is not None:
                timezone = tz

        # Update the cache.
        pipe.set(format_key("user:{0}:name".format(user)), name)
        pipe.set(format_key("user:{0}:etag".format(user)), etag)
        pipe.set(format_key("user:{0}:gravatar".format(user)), gravatar)
        if timezone is not None:
            pipe.set(format_key("user:{0}:tz".format(user)), timezone)
        pipe.execute()

    return {
        "username": username,
        "name": name if name is not None else username,
        "gravatar": gravatar if gravatar is not None else "none",
        "timezone": int(timezone) if timezone is not None else None,
    }


def get_social_stats(username, max_connected=5, max_users=50):
    r = get_connection()
    pipe = r.pipeline()
    user = username.lower()

    # Find the connected users.
    connection_key = format_key("social:connection:{0}".format(user))
    pipe.exists(connection_key)
    pipe.zrevrange(connection_key, 0, max_connected-1)
    pipe.zrevrange(format_key("social:user:{0}".format(user)), 0, -1,
                   withscores=True)
    flag, connected_users, repos = pipe.execute()
    if not flag:
        [pipe.zrevrange(format_key("social:repo:{0}".format(repo)), 0,
                        max_users)
         for repo, count in repos]
        users = pipe.execute()
        [pipe.zincrby(connection_key, u, 1) for l in users for u in l
         if u != user]
        pipe.expire(connection_key, 172800)
        pipe.zrevrange(connection_key, 0, max_connected-1)
        connected_users = pipe.execute()[-1]

    # Get the nearest neighbors in behavior space.
    similar_users = get_neighbors(user)
    [pipe.get(format_key("user:{0}:name".format(u)))
     for u in connected_users + similar_users]
    names = pipe.execute()

    # Parse all the users.
    users = [{"username": u, "name": n.decode("utf-8") if n is not None else u}
             for u, n in zip(connected_users+similar_users, names)]

    nc = len(connected_users)
    return {
        "connected_users": users[:nc],
        "similar_users": users[nc:],
        "repositories": [{"repo": repo, "count": int(count)}
                         for repo, count in repos[:5]],
    }


def make_histogram(data, size, offset=0):
    result = [0] * size
    for k, v in data:
        val = float(v)
        i = int(k) + offset
        while (i < 0):
            i += size
        result[i % size] = val
    return result


def get_usage_stats(username):
    user = username.lower()
    pipe = get_pipeline()

    # Get the total number of events performed by this user.
    pipe.zscore(format_key("user"), user)

    # The timezone estimate.
    pipe.get(format_key("user:{0}:tz".format(user)))

    # Get the top <= 5 most common events.
    pipe.zrevrangebyscore(format_key("user:{0}:event".format(user)),
                          "+inf", 0, 0, 5, withscores=True)

    # The average daily and weekly schedules.
    pipe.hgetall(format_key("user:{0}:hour".format(user)))
    pipe.hgetall(format_key("user:{0}:day".format(user)))

    # The language stats.
    pipe.zrevrange(format_key("user:{0}:lang".format(user)), 0, -1,
                   withscores=True)

    # Parse the results.
    results = pipe.execute()
    total_events = int(results[0]) if results[0] is not None else 0
    if not total_events:
        return None
    timezone = results[1]
    offset = int(timezone) + 8 if timezone is not None else 0
    event_counts = results[2]
    daily_histogram = make_histogram(results[3].items(), 24, offset)
    weekly_histogram = make_histogram(results[4].items(), 7)
    languages = results[5]

    # Parse the languages into a nicer form and get quantiles.
    [(pipe.zcount(format_key("lang:{0}:user".format(l)), 100, "+inf"),
      pipe.zrevrank(format_key("lang:{0}:user".format(l)), user))
     for l, c in languages]
    quants = pipe.execute()
    languages = [{"language": l,
                  "quantile": (min([100, int(100 * float(pos) / tot) + 1])
                               if tot > 0 and pos is not None
                               else 100),
                  "count": int(c)}
                 for (l, c), tot, pos in zip(languages, quants[::2],
                                             quants[1::2])]

    # Generate some stats for the event specific event types.
    [(pipe.hgetall(format_key("user:{0}:event:{1}:day".format(user, e))),
      pipe.hgetall(format_key("user:{0}:event:{1}:hour".format(user, e))))
     for e, c in event_counts]
    results = pipe.execute()
    events = [{"type": e[0],
               "total": int(e[1]),
               "week": map(int, make_histogram(w.items(), 7)),
               "day": map(int, make_histogram(d.items(), 24, offset))}
              for e, w, d in zip(event_counts, results[::2], results[1::2])]

    return {
        "total": total_events,
        "events": events,
        "day": map(int, daily_histogram),
        "week": map(int, weekly_histogram),
        "languages": languages,
    }


def get_comparison(user1, user2):
    # Normalize the usernames.
    user1, user2 = user1.lower(), user2.lower()

    # Grab the stats from the database.
    pipe = get_pipeline()
    pipe.zscore(format_key("user"), user1)
    pipe.zscore(format_key("user"), user2)
    pipe.zrevrange(format_key("user:{0}:event".format(user1)), 0, -1,
                   withscores=True)
    pipe.zrevrange(format_key("user:{0}:event".format(user2)), 0, -1,
                   withscores=True)
    pipe.zrevrange(format_key("user:{0}:lang".format(user1)), 0, -1,
                   withscores=True)
    pipe.zrevrange(format_key("user:{0}:lang".format(user2)), 0, -1,
                   withscores=True)
    pipe.hgetall(format_key("user:{0}:day".format(user1)))
    pipe.hgetall(format_key("user:{0}:day".format(user2)))
    raw = pipe.execute()

    # Get the total number of events.
    total1 = float(raw[0]) if raw[0] is not None else 0
    total2 = float(raw[1]) if raw[1] is not None else 0
    if not total1:
        return "is more active on GitHub"
    elif not total2:
        return "is less active on GitHub"

    # Load the event types from disk.
    with flask.current_app.open_resource("event_types.json") as f:
        evttypes = json.load(f)

    # Compare the fractional event types.
    evts1 = dict(raw[2])
    evts2 = dict(raw[3])
    diffs = []
    for e, desc in evttypes.iteritems():
        if e in evts1 and e in evts2:
            d = float(evts2[e]) / total2 / float(evts1[e]) * total1
            if d != 1:
                more = "more" if d > 1 else "less"
                if d > 1:
                    d = 1.0 / d
                diffs.append((desc.format(more=more, user=user2), d * d))

    # Compare language usage.
    langs1 = dict(raw[4])
    langs2 = dict(raw[5])
    for l in set(langs1.keys()) | set(langs2.keys()):
        n = float(langs1.get(l, 0)) / total1
        d = float(langs2.get(l, 0)) / total2
        if n != d and d > 0:
            if n > 0:
                d = d / n
            else:
                d = 1.0 / d
            more = "more" if d > 1 else "less"
            desc = "is {{more}} of a {0} aficionado".format(l)
            if d > 1:
                d = 1.0 / d
            diffs.append((desc.format(more=more), d * d))

    # Number of languages.
    nl1, nl2 = len(raw[4]), len(raw[5])
    if nl1 and nl2:
        desc = "speaks {more} languages"
        if nl1 > nl2:
            diffs.append((desc.format(more="fewer"),
                          nl2 * nl2 / nl1 / nl1))
        else:
            diffs.append((desc.format(user=user2, more="more"),
                          nl1 * nl1 / nl2 / nl2))

    # Compare the average weekly schedules.
    week1 = map(lambda v: int(v[1]), raw[6].iteritems())
    week2 = map(lambda v: int(v[1]), raw[7].iteritems())
    mu1, mu2 = sum(week1) / 7.0, sum(week2) / 7.0
    var1 = np.sqrt(sum(map(lambda v: (v - mu1) ** 2, week1)) / 7.0) / mu1
    var2 = np.sqrt(sum(map(lambda v: (v - mu2) ** 2, week2)) / 7.0) / mu2
    if var1 or var2 and var1 != var2:
        if var1 > var2:
            diffs.append(("has a more consistent weekly schedule", var2/var1))
        else:
            diffs.append(("has a less consistent weekly schedule", var1/var2))

    # Compute the relative probabilities of the comparisons and normalize.
    ps = map(lambda v: v[1], diffs)
    norm = sum(ps)

    # Choose a random description weighted by the probabilities.
    return np.random.choice([d[0] for d in diffs], p=[p / norm for p in ps])


def get_repo_info(username, reponame, maxusers=50, max_recommend=5):
    # Normalize the repository name.
    repo = "{0}/{1}".format(username, reponame)
    rkey = format_key("social:repo:{0}".format(repo))
    recommend_key = format_key("social:recommend:{0}".format(repo))

    # Get the list of users.
    pipe = get_pipeline()
    pipe.exists(rkey)
    pipe.exists(recommend_key)
    pipe.zrevrange(recommend_key, 0, max_recommend-1)
    pipe.zrevrange(rkey, 0, maxusers, withscores=True)
    flag1, flag2, recommendations, users = pipe.execute()
    if not flag1:
        return None

    if not flag2:
        # Compute the repository similarities.
        [pipe.zrevrange(format_key("social:user:{0}".format(u)), 0, -1)
         for u, count in users]
        repos = pipe.execute()
        [pipe.zincrby(recommend_key, r, 1) for l in repos for r in l
         if r != repo]
        pipe.expire(recommend_key, 172800)
        pipe.zrevrange(recommend_key, 0, max_recommend-1)
        recommendations = pipe.execute()[-1]

    # Get the contributor names.
    users = users[:5]
    [pipe.get(format_key("user:{0}:name".format(u))) for u, count in users]
    names = pipe.execute()

    return {
        "repository": repo,
        "recommendations": recommendations,
        "contributors": [{"username": u, "name": n.decode("utf-8")
                          if n is not None else u,
                          "count": int(count)}
                         for (u, count), n in zip(users, names)]
    }
