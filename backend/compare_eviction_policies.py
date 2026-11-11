
import random
import redis


REDIS_URL = "redis://localhost:6380/0"
POLICIES = [
    "allkeys-lru",
    "allkeys-lfu",
    "allkeys-random",
]

TEST_KEY_PREFIX = "eviction_test:"
KEY_COUNT = 2000
VALUE_SIZE = 4096


def run_redis_experiment(policy: str) -> dict:
    client = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    client.flushdb()
    client.config_set("maxmemory", "5mb")
    client.config_set("maxmemory-policy", policy)

    # Insert 2,000 keys with 4 KB values.
    value = "x" * VALUE_SIZE

    for index in range(KEY_COUNT):
        client.set(f"{TEST_KEY_PREFIX}{index}", value)

    keys_after_insertion = client.dbsize()

    # Frequently access the first 100 keys.
    for _ in range(10):
        for index in range(100):
            client.get(f"{TEST_KEY_PREFIX}{index}")

    # Access the last 100 keys once.
    for index in range(KEY_COUNT - 100, KEY_COUNT):
        client.get(f"{TEST_KEY_PREFIX}{index}")

    remaining_keys = client.keys(f"{TEST_KEY_PREFIX}*")

    result = {
        "policy": policy,
        "keys_after_insertion": keys_after_insertion,
        "remaining_keys": len(remaining_keys),
        "memory_used": client.info("memory")["used_memory_human"],
        "maxmemory": client.config_get("maxmemory")["maxmemory"],
    }

    client.close()
    return result


def run_fifo_experiment() -> dict:
    # FIFO simulation using Python insertion order.
    entries = {}

    for index in range(KEY_COUNT):
        entries[f"{TEST_KEY_PREFIX}{index}"] = "x" * VALUE_SIZE

    # Simulate a limited cache by retaining only the newest 500 keys.
    while len(entries) > 500:
        oldest_key = next(iter(entries))
        del entries[oldest_key]

    return {
        "policy": "FIFO (Python simulation)",
        "keys_after_insertion": KEY_COUNT,
        "remaining_keys": len(entries),
        "memory_used": "Not measured",
        "maxmemory": "500-key limit",
    }


def main():
    random.seed(42)

    print("\nREDIS EVICTION POLICY COMPARISON")
    print("=" * 65)

    for policy in POLICIES:
        result = run_redis_experiment(policy)
        print(result)

    print(run_fifo_experiment())

    print("\nExperiment completed.")


if __name__ == "__main__":
    main()
