#include "t6_fe_recovery.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    struct t6_fe_state s;
    t6_fe_init(&s);
    assert(t6_fe_request(&s, T6_FE_NORMAL));
    assert(t6_fe_take_pending(&s) == T6_FE_NORMAL);
    assert(t6_fe_take_pending(&s) == 0);
    assert(!t6_fe_request(&s, T6_FE_DEFERRED));
    assert(!t6_fe_request(&s, (enum t6_fe_request)3));
    assert(t6_fe_take_pending(&s) == 0);
    s.deferred = true;
    assert(t6_fe_request(&s, T6_FE_DEFERRED));
    assert(t6_fe_take_pending(&s) == T6_FE_DEFERRED);
    const unsigned expected[] = {5000, 10000, 20000, 40000, 40000};
    for (unsigned i = 0; i < 5; i++)
        assert(t6_fe_failure(&s) == expected[i]);
    assert(!s.exhausted);
    assert(t6_fe_failure(&s) == 0);
    assert(s.exhausted);
    assert(!t6_fe_request(&s, T6_FE_DEFERRED));
    assert(t6_fe_request(&s, T6_FE_NORMAL));
    assert(!t6_fe_request(&s, T6_FE_NORMAL));
    /* Normal work must survive; stale deferred work must not. */
    s.pending |= T6_FE_DEFERRED;
    t6_fe_success(&s);
    assert(t6_fe_take_pending(&s) == T6_FE_NORMAL);
    assert(!s.exhausted && !s.recheck_used && s.failures == 0);
    t6_fe_stop(&s);
    assert(!t6_fe_request(&s, T6_FE_NORMAL));
    assert(t6_fe_take_pending(&s) == 0);
    puts("FE reference state transitions: PASS");
    return 0;
}
