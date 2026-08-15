$containers = @(
  'satoruemr-nouveau-1',
  'satoruemr-couchdb-1',
  'satoruemr-haproxy-1',
  'satoruemr-api-1',
  'satoruemr-sentinel-1',
  'satoruemr-nginx-1',
  'satoruemr-dir-cht-upgrade-service-1'
)
foreach ($c in $containers) {
  $lines = wsl docker inspect $c --format "{{.Created}}|{{.RestartCount}}|{{.State.StartedAt}}|{{.State.Status}}"
  $data = $lines -split '\|'
  Write-Output ("{0,-45} Created: {1}  Restarts: {2}  Started: {3}  Status: {4}" -f $c, $data[0], $data[1], $data[2], $data[3])
}