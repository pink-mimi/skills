param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $Arguments
)

$runPy = Join-Path $PSScriptRoot 'run.py'
$pythonPath = $null
$pythonPrefix = @()

if ($env:GITHUB_HOT_PYTHON -and (Test-Path -LiteralPath $env:GITHUB_HOT_PYTHON)) {
  $pythonPath = $env:GITHUB_HOT_PYTHON
}

if (-not $pythonPath) {
  foreach ($name in @('python', 'python3')) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if ($command) { $pythonPath = $command.Source; break }
  }
}

if (-not $pythonPath) {
  $pyLauncher = Get-Command 'py' -ErrorAction SilentlyContinue
  if ($pyLauncher) { $pythonPath = $pyLauncher.Source; $pythonPrefix = @('-3') }
}

if (-not $pythonPath) {
  $codexPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
  if (Test-Path -LiteralPath $codexPython) { $pythonPath = $codexPython }
}

if (-not $pythonPath) {
  Write-Error 'Python 3 was not found. Install Python 3 or set GITHUB_HOT_PYTHON to its full path.'
  exit 127
}

& $pythonPath @pythonPrefix $runPy @Arguments
exit $LASTEXITCODE
