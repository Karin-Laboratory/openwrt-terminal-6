// SPDX-License-Identifier: MIT
/* Build-only AArch64 PID1 diagnostic: no network, flash or recovery actions. */
struct timespec_local { long tv_sec; long tv_nsec; };
static inline long syscall4(long number, long a0, long a1, long a2, long a3)
{
    register long x0 __asm__("x0") = a0;
    register long x1 __asm__("x1") = a1;
    register long x2 __asm__("x2") = a2;
    register long x3 __asm__("x3") = a3;
    register long x8 __asm__("x8") = number;
    __asm__ volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x8) : "memory");
    return x0;
}

__attribute__((noreturn)) void _start(void)
{
    static const char banner[] =
        "Air6 AP-first ARM64 diagnostic PID1 (build-only; no networking)\n";
    const struct timespec_local delay = {5, 0};
    long fd = syscall4(56, -100, (long)"/dev/console", 1, 0); /* openat */
    if (fd < 0)
        fd = 1;
    syscall4(64, fd, (long)banner, sizeof(banner) - 1, 0); /* write */
    for (;;)
        syscall4(115, 1, 0, (long)&delay, 0); /* clock_nanosleep */
}
