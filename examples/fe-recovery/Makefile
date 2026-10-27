# SPDX-License-Identifier: MIT
CC ?= cc
CFLAGS ?= -O2 -g -Wall -Wextra -Werror -std=c11
.PHONY: test clean
test: test_fe_recovery
	./test_fe_recovery
test_fe_recovery: test_fe_recovery.c t6_fe_recovery.h
	$(CC) $(CFLAGS) -o $@ test_fe_recovery.c
clean:
	rm -f test_fe_recovery
