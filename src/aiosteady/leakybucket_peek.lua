-- this is required to be able to use TIME and writes; basically it lifts the script into IO
redis.replicate_commands()
-- make some nicer looking variable names:
local retval = nil

-- Redis documentation recommends passing the keys separately so that Redis
-- can - in the future - verify that they live on the same shard of a cluster, and
-- raise an error if they are not. As far as can be understood this functionality is not
-- yet present, but if we can make a little effort to make ourselves more future proof
-- we should.
local bucket_level_key = KEYS[1]

-- and the config variables
local max_bucket_capacity = tonumber(ARGV[1])
local recharge = tonumber(ARGV[2])

-- Take the Redis timestamp
local redis_time = redis.call("TIME") -- Array of [seconds, microseconds]
local now = tonumber(redis_time[1]) + (tonumber(redis_time[2]) / 1000000)
local key_lifetime = math.ceil(max_bucket_capacity * recharge)

-- get current bucket level. The throttle key might not exist yet in which
-- case we default to 0
local bucket_level = 0
local last_updated = now -- use sensible default of 'now' if the key does not exist

local key_data = redis.call("GET", bucket_level_key)
if key_data ~= false then
  local blocked_until = 0
  for a, b, c in string.gmatch(key_data, "(%S+) (%S+) (%S+)") do
    bucket_level = tonumber(a)
    last_updated = tonumber(b)
    blocked_until = tonumber(c)
  end

  local num_recharges = math.floor((now - last_updated) / recharge)
  bucket_level = math.max(0, bucket_level - num_recharges)

  if num_recharges > 0 then
    last_updated = last_updated + num_recharges * recharge
    last_updated = math.min(last_updated, now)
  end

  if blocked_until > now then
    return {tostring(blocked_until - now), bucket_level, "0.0"}
    end
end

local to_next = tostring(last_updated + recharge - now)
retval = {0, bucket_level, to_next}

return retval