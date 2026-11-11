# CacheRAG --- One-Page Caching Design Summary

## 1. Purpose and design

CacheRAG uses caching to reduce repeated retrieval and LLM-generation
work while keeping answers scoped to the correct document collection and
its current version. Redis is the primary answer cache; Qdrant stores
semantic-cache vectors so that sufficiently similar questions can be
considered for reuse.

The design follows the **cache-aside** pattern: the application checks
the cache before doing the expensive RAG work. A cached answer is
returned when a valid entry is found. On a miss, CacheRAG continues
through embedding, retrieval, reranking, and answer generation, then
stores a successful answer for later requests.

## 2. Cache lookup and storage flow

1.  Build an exact cache key using the collection ID, collection
    version, normalized question, and web-search mode.
2.  Check Redis for that key. An exact hit returns the saved answer and
    sources without repeating document retrieval or LLM generation.
3.  On an exact miss, create a question embedding and search the
    semantic cache, scoped to the same collection, collection version,
    and web-search mode.
4.  Reuse a semantic result only when its similarity meets the
    configured threshold and its referenced Redis answer still exists.
5.  If no valid cache entry is found, run the normal RAG pipeline:
    hybrid document retrieval, reranking, and answer generation.
6.  Save successful answers in Redis with their sources and TTL. Store a
    corresponding semantic-cache entry only when the Redis write
    succeeds.

Questions that cannot be answered from the selected documents are not
treated as successful reusable answers.

## 3. TTL and invalidation

Redis entries have a configurable time-to-live (TTL). Expiration limits
how long an answer can remain reusable. The semantic index in Qdrant can
retain a reference after its Redis answer expires; CacheRAG checks Redis
before reusing that reference and removes stale references when Redis is
reachable but the answer is missing.

Document changes must not reuse answers generated from an older
collection state. Cache keys include the collection version, and
collection update/deletion workflows invalidate the collection's Redis
answer entries and semantic-cache entries. This combination helps
prevent stale answers from being served after the underlying documents
change.

## 4. Eviction policies and trade-offs

Redis memory is bounded and the configured production policy is
**`allkeys-lru`**.

  -----------------------------------------------------------------------
  Policy                  Eviction principle      Main trade-off
  ----------------------- ----------------------- -----------------------
  LRU                     Removes keys that have  Works well when
                          not been used recently  recently used answers
                                                  are likely to be
                                                  requested again; can
                                                  evict less-frequently
                                                  used but important
                                                  entries

  LFU                     Removes keys with lower Preserves frequently
                          access frequency        reused answers;
                                                  frequency can take time
                                                  to reflect changing
                                                  workloads

  FIFO                    Removes keys in         Simple age-based
                          insertion order         behavior; ignores how
                                                  often or how recently
                                                  an answer is used

  Random                  Removes a randomly      Simple selection; may
                          selected key            evict a highly useful
                                                  answer
  -----------------------------------------------------------------------

An isolated Redis experiment compared LRU, LFU, and random under a small
memory limit. FIFO was simulated separately in Python, so these results
are exploratory rather than a controlled, directly comparable benchmark.
The production configuration remains `allkeys-lru`; the choice should be
revisited if measured workload behavior indicates a better fit.

## 5. Redis-unavailable behavior

Redis is an optimization, not a requirement for answering a question. If
a Redis read fails, CacheRAG treats the lookup as a miss and continues
with normal document retrieval and answer generation. If a Redis write
fails, the answer can still be returned, but it is not recorded as a
successful Redis cache write. When Redis availability cannot be
confirmed, CacheRAG avoids deleting semantic-cache references merely
because their Redis lookup failed.

The failure-handling logic has been verified with mocked Redis
connection errors. A real Redis network-outage test remains a separate
final verification item.

## 6. Evaluation evidence to present

The evaluation should demonstrate:

-   **Cache miss:** first request performs the RAG pipeline and attempts
    to cache the successful answer.
-   **Exact cache hit:** repeat the same question and show that the
    saved answer is returned without repeating retrieval or generation.
-   **Semantic cache hit:** ask a sufficiently similar question and show
    reuse only when the similarity threshold and Redis validation pass.
-   **TTL and invalidation:** show expiration and verify that document
    updates/deletions prevent reuse of old answers.
-   **Failure and memory behavior:** demonstrate Redis-unavailable
    fallback and explain the eviction-policy comparison.
-   **Performance:** report cache hit rate and compare cached versus
    uncached response time; include cache lookup, embedding, retrieval,
    reranking, LLM, and cache-write timings where available.

**Current evidence note:** Cache service and RAG fallback checks have
passed mocked Redis-failure tests, and an initial eviction experiment
has been run. The frontend miss/exact-hit/semantic-hit demonstration,
real Redis outage check, and final performance charts/statistics still
need to be captured before claiming the full mentor evaluation is
complete.
