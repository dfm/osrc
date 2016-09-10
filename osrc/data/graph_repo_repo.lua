local social_key = ARGV[1]..":s:r:"..KEYS[1]..":r"
if redis.call("EXISTS", social_key) == 0 then
    local users = redis.call("ZREVRANGE", ARGV[1]..":r:"..KEYS[1]..":u", 0, 5,"withscores")
    for i,user_or_score in ipairs(users) do
        if i%2 == 1 then
            local user = user_or_score
            local user_score = users[i+1]

            local repos = redis.call("ZREVRANGE", ARGV[1]..":u:"..user..":r", 0, 5, "withscores")
            for j,repo_or_score in ipairs(repos) do
                if j%2 == 1 then
                    local repo = repo_or_score
                    if repo ~= KEYS[1] then
                        redis.call("ZINCRBY", social_key, user_score + repos[j+1], repo)
                    end
                end
            end
        end
    end

    redis.call("EXPIRE", social_key, 172800)
end
return redis.call("ZREVRANGE", social_key, 0, 4, "withscores")
