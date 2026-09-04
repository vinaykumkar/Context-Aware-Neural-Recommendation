# Watchdog: rerun stage 2 until it completes (resumable pipeline).
# Used because this machine's constrained memory can terminate long runs;
# every stage of build_models.py resumes from cached parts.
$max = 12
for ($i = 1; $i -le $max; $i++) {
    Write-Output "=== watchdog attempt $i ==="
    python -u scripts/build_models.py
    if ($LASTEXITCODE -eq 0) { Write-Output "stage 2 finished OK"; break }
    Write-Output "attempt $i exited with $LASTEXITCODE - resuming"
    Start-Sleep -Seconds 3
}
