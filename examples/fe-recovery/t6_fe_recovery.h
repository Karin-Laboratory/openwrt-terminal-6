/* Independent reference state machine for MT6990 FE recovery research.
 * Not linked to the kernel or used on hardware. No vendor source included.
 * This example models retry budget and shutdown only; callers supply locking.
 */
#ifndef T6_FE_RECOVERY_H
#define T6_FE_RECOVERY_H
#include <stdbool.h>
#include <stdint.h>

enum t6_fe_request { T6_FE_NORMAL = 1, T6_FE_DEFERRED = 2 };
struct t6_fe_state {
    bool shutdown;
    bool deferred;
    bool exhausted;
    bool recheck_used;
    unsigned failures;
    unsigned pending;
};

/* Pure transitions: caller must serialize across worker and teardown. */
static inline void t6_fe_init(struct t6_fe_state *s)
{
    *s = (struct t6_fe_state){0};
}

static inline void t6_fe_stop(struct t6_fe_state *s)
{
    s->shutdown = true;
    s->pending = 0;
    s->deferred = false;
}

static inline bool t6_fe_request(struct t6_fe_state *s, enum t6_fe_request req)
{
    if (s->shutdown)
        return false;
    if (req == T6_FE_DEFERRED && (!s->deferred || s->exhausted))
        return false;
    if (req == T6_FE_NORMAL && s->exhausted) {
        if (s->recheck_used)
            return false;
        s->recheck_used = true;
    }
    s->pending |= (unsigned)req;
    return true;
}

static inline unsigned t6_fe_take_pending(struct t6_fe_state *s)
{
    unsigned pending = s->pending;
    s->pending = 0;
    return s->shutdown ? 0 : pending;
}

/* Returns milliseconds until the next retry, or 0 if the budget is exhausted.
 * Modem-busy handling is separate: this is only a failed FE recovery.
 */
static inline unsigned t6_fe_failure(struct t6_fe_state *s)
{
    static const unsigned backoff_ms[] = {5000, 10000, 20000, 40000, 40000};
    if (s->shutdown || s->exhausted)
        return 0;
    if (s->failures >= sizeof(backoff_ms) / sizeof(backoff_ms[0])) {
        s->exhausted = true;
        return 0;
    }
    unsigned delay = backoff_ms[s->failures++];
    if (s->failures == sizeof(backoff_ms) / sizeof(backoff_ms[0]))
        s->exhausted = true;
    return delay;
}

static inline void t6_fe_success(struct t6_fe_state *s)
{
    if (s->shutdown)
        return;
    s->deferred = false;
    s->exhausted = false;
    s->recheck_used = false;
    s->failures = 0;
}
#endif
