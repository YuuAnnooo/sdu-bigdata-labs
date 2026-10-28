# Download 10 English documents (plain text) from a public web source.
#   - Wikipedia action API with explaintext=1 returns article plain text.
# Output:
#   corpus/raw/documentNN.txt   pure document body (no metadata header)
#   corpus/manifest.tsv         file / title / source url / word count
$ErrorActionPreference = 'Stop'
$outDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\corpus\raw'))
$manifestPath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\corpus\manifest.tsv'))
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$topics = @(
  @{ title = 'Apache Hadoop';          url = 'https://en.wikipedia.org/wiki/Apache_Hadoop' },
  @{ title = 'MapReduce';              url = 'https://en.wikipedia.org/wiki/MapReduce' },
  @{ title = 'Inverted index';         url = 'https://en.wikipedia.org/wiki/Inverted_index' },
  @{ title = 'Apache Spark';           url = 'https://en.wikipedia.org/wiki/Apache_Spark' },
  @{ title = 'Big data';               url = 'https://en.wikipedia.org/wiki/Big_data' },
  @{ title = 'Search engine indexing'; url = 'https://en.wikipedia.org/wiki/Search_engine_indexing' },
  @{ title = 'Lucene';                 url = 'https://en.wikipedia.org/wiki/Apache_Lucene' },
  @{ title = 'Distributed computing';  url = 'https://en.wikipedia.org/wiki/Distributed_computing' },
  @{ title = 'Data mining';            url = 'https://en.wikipedia.org/wiki/Data_mining' },
  @{ title = 'Cloud computing';        url = 'https://en.wikipedia.org/wiki/Cloud_computing' }
)

$maxWords = 1300
$rows = New-Object System.Collections.Generic.List[string]
$rows.Add("file`ttitle`turl`twords")
$i = 0
foreach ($t in $topics) {
  $i++
  $name = 'document{0:D2}.txt' -f $i
  $api = 'https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&redirects=1&titles=' + [uri]::EscapeDataString($t.title)
  $resp = Invoke-RestMethod -Uri $api -TimeoutSec 60 -Headers @{ 'User-Agent' = 'sdu-bigdata-course-lab/1.0' }
  $page = $resp.query.pages.PSObject.Properties.Value | Select-Object -First 1
  $text = [string]$page.extract
  if (-not $text) { throw "empty extract for $($t.title)" }

  foreach ($marker in @("`n`nReferences`n", "`n`nSee also`n", "`n`nNotes`n", "`n`nFurther reading`n", "`n`nExternal links`n")) {
    $idx = $text.IndexOf($marker)
    if ($idx -gt 0) { $text = $text.Substring(0, $idx) }
  }
  $text = $text -replace "`r`n", "`n"
  $text = $text -replace "[ \t]+", " "
  $text = $text -replace "`n{3,}", "`n`n"
  $text = $text.Trim()

  $words = $text -split '\s+'
  if ($words.Count -gt $maxWords) {
    $paras = $text -split "`n`n"
    $acc = New-Object System.Collections.Generic.List[string]
    $n = 0
    foreach ($p in $paras) {
      $pw = ($p -split '\s+').Count
      if ($n + $pw -gt $maxWords) { break }
      $acc.Add($p); $n += $pw
    }
    $text = ($acc -join "`n`n")
  }

  [System.IO.File]::WriteAllText((Join-Path $outDir $name), $text + "`n", (New-Object System.Text.UTF8Encoding($false)))
  $wc = ($text -split '\s+').Count
  $rows.Add("$name`t$($t.title)`t$($t.url)`t$wc")
  "{0} <- {1} ({2} words)" -f $name, $t.title, $wc
}
[System.IO.File]::WriteAllLines($manifestPath, $rows, (New-Object System.Text.UTF8Encoding($false)))
"manifest -> $manifestPath"
