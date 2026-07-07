We use Bencher to monitor performance over time.

Because running benchmarks on GitHub Actions is very prone to "noisy neighbours"
our bencher threshold uses IQR, which needs a bit of run history, but is
resilient to outlier CI runs that are just randomly slow.

Beware of 2 things:

# stable test names
Ensure stable benchmark test names; when parametrising tests, pytest will generate
test names. If these are different every time, then all benchmarks will only ever
have a history of 1, which defeats this

# assert hard upper bounds on durations
Assert (generous) hard upper bounds with the `benchmark_assertions` fixture.
In order to avoid the "boiling frog" effect of slow regression where over time
performance gets slowly worse, but in steps small enough not to trigger a
Bencher.dev alarm.
This way when a benchmark has obviously gotten too slow it will fail the test
and we can analyse the trends using the history of runs on bencher if the cause
is not clearly from this PR.
