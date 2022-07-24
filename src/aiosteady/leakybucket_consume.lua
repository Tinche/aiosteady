-- The return values are:
-- * success (bool)
-- * block duration remaining (float)
-- * current bucket level (int)
-- * seconds to next drop (float)

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
local recharge_time = tonumber(ARGV[2])
local block_duration = tonumber(ARGV[3])

-- n_tokens can be negative, which removes drops from the bucket, up to zero.
local n_tokens = tonumber(ARGV[4]) -- How many tokens this call adds to the bucket. Defaults to 1

-- Take the Redis timestamp
local redis_time = redis.call("TIME") -- Array of [seconds, microseconds]
local now = tonumber(redis_time[1]) + (tonumber(redis_time[2]) / 1000000)
local key_lifetime = 0

-- get current bucket level. The throttle key might not exist yet in which
-- case we default to 0
local bucket_level = 0
local last_updated = now -- use sensible default of 'now' if the key does not exist
local blocked_until = 0

local key_data = redis.call("GET", bucket_level_key)
if key_data ~= false then
  for a, b, c in string.gmatch(key_data, "(%S+) (%S+) (%S+)") do
    bucket_level = tonumber(a)
    last_updated = tonumber(b)
    blocked_until = tonumber(c)
  end

  if blocked_until > now then
    return {false, tostring(blocked_until - now), 0, 0}
  end

  local num_recharges = math.floor((now - last_updated) / recharge_time)
  bucket_level = math.max(0, bucket_level - num_recharges)

  if num_recharges > 0 then
    last_updated = last_updated + num_recharges * recharge_time
    last_updated = math.min(last_updated, now)
  end
end

local next_drop_in = tostring(last_updated + recharge_time - now)
local new_level = bucket_level + n_tokens

if new_level <= 0 then
  retval = {true, 0, 0, ARGV[2]}  -- ARGV[2] is recharge as a string
elseif new_level <= max_bucket_capacity then
  bucket_level = new_level
  key_lifetime = bucket_level * recharge_time
  retval = {true, 0, bucket_level, next_drop_in}
else
  if block_duration ~= 0 then
    blocked_until = now + block_duration
    key_lifetime = math.max(block_duration, bucket_level * recharge_time)
    retval = {false, tostring(block_duration), 0, next_drop_in}
  else
    -- No need to update the Redis state, just return failure.
    key_lifetime = bucket_level * recharge_time
    return {false, tostring(block_duration), max_bucket_capacity, next_drop_in}
  end
end

if key_lifetime == 0 then
  redis.call("DEL", bucket_level_key)
else
  redis.call("SETEX", bucket_level_key, key_lifetime, string.format("%d %f %f", bucket_level, last_updated, blocked_until))
end

return retval