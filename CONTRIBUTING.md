# Contributing

Describe the problem and expected behavior before changing the engine. For a
bug, include Python/OS version, reproducible configuration, actual outcome, and
relevant exported events. Keep personal file contents out of bug reports.

Create a focused branch from `main`. Preserve definitions for rates, observation
points, recovery, retry budgets, and unavailable metrics. Avoid fabricated results
or assertions based only on simulated delays when real sockets are involved.

Run `python -m unittest discover -v`. For changes affecting demo recovery, also
run `python -m tests.run_demo` and inspect the saved raw measurements. For UI
changes, check the actual controls, narrow layouts, exports, and both themes.

PRs should state the problem, resulting behavior, and validation performed.
Use your own Git identity and a verified account email. Link relevant issues
and include reproducible validation results for reviewers.
