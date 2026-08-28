# Run full migration pipeline against sample-bank landscape
param(
    [string]$SourceRoot = "$PSScriptRoot\..\sample-bank",
    [string]$Landscape = "$PSScriptRoot\..\sample-bank\landscape-manifest.yaml",
    [string]$ProjectName = "EuroSA Bank Migration",
    [switch]$AutoApprove
)

$ErrorActionPreference = "Stop"
$PlatformDir = Join-Path $PSScriptRoot "..\platform"
Push-Location $PlatformDir

try {
    if (-not (Get-Command migrate-framework -ErrorAction SilentlyContinue)) {
        Write-Host "Installing migrate_framework..."
        pip install -e ".[dev]" | Out-Null
    }
    $cli = "python -m migrate_framework.cli"
    if (Get-Command migrate-framework -ErrorAction SilentlyContinue) {
        $cli = "migrate-framework"
    }

    Write-Host "Initializing project..."
    $initJson = Invoke-Expression "$cli init --name '$ProjectName' --source '$SourceRoot' --landscape '$Landscape'" | ConvertFrom-Json
    $projectId = $initJson.project_id
    Write-Host "Project ID: $projectId"

    $stages = @("discover", "ingest", "graph", "diagnose", "hypothesize", "recommend", "plan", "playbook")
    $approvalStages = @("ingest", "diagnose", "hypothesize", "recommend", "plan")

    foreach ($stage in $stages) {
        if ($approvalStages -contains $stage) {
            if ($AutoApprove) {
                Invoke-Expression "$cli approve --project-id $projectId --stage $stage --by pipeline-script" | Out-Null
            } else {
                Write-Host "Approve gate required for stage: $stage"
                Invoke-Expression "$cli approve --project-id $projectId --stage $stage --by operator" | Out-Null
            }
        }
        Write-Host "Running stage: $stage"
        Invoke-Expression "$cli run --project-id $projectId --stage $stage" | Out-Null
    }

    Write-Host "`nPipeline complete. Project status:"
    Invoke-Expression "$cli status --project-id $projectId"
}
finally {
    Pop-Location
}
