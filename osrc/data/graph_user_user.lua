local social_key = ARGV[1]..":s:u:"..KEYS[1]..":u"
if redis.call("EXISTS", social_key) == 0 then
    local repos = redis.call("ZREVRANGE", ARGV[1]..":u:"..KEYS[1]..":r", 0, 5,"withscores")
    for i,repo_or_score in ipairs(repos) do
        if i%2 == 1 then
            local repo = repo_or_score
            local repo_score = repos[i+1]

            local users = redis.call("ZREVRANGE", ARGV[1]..":r:"..repo..":u", 0, 5, "withscores")
            for j,user_or_score in ipairs(users) do
                if j%2 == 1 then
                    local user = user_or_score
                    if user ~= KEYS[1] then
                        redis.call("ZINCRBY", social_key, repo_score + users[j+1], user)
                    end
                end
            end
        end
    end
    redis.call("EXPIRE", social_key, 172800)
end
return redis.call("ZREVRANGE", social_key, 0, 4, "withscores")
