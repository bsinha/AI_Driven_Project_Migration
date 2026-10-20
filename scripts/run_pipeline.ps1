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
        throw "migrate-framework is not installed. Set up the platform environment explicitly before running the demo."
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
        Write-Host "Running stage: $stage"
        Invoke-Expression "$cli run --project-id $projectId --stage $stage" | Out-Null
        if ($approvalStages -contains $stage) {
            if ($AutoApprove) {
                Invoke-Expression "$cli approve --project-id $projectId --stage $stage --by isolated-demo" | Out-Null
            } else {
                $decision = Read-Host "Stage '$stage' completed. Enter approve, reject, or stop"
                if ($decision -eq "approve") {
                    Invoke-Expression "$cli approve --project-id $projectId --stage $stage --by operator" | Out-Null
                } elseif ($decision -eq "reject") {
                    $reasonCodes = @(
                        "insufficient_evidence", "wrong_boundary", "risk_too_high",
                        "sme_disagreement", "low_confidence", "inconsistent_with_discovery", "other"
                    )
                    Write-Host "Reason codes: $($reasonCodes -join ', ')"
                    $reasonCode = Read-Host "Rejection reason code"
                    if ($reasonCodes -notcontains $reasonCode) {
                        throw "Invalid rejection reason code '$reasonCode'."
                    }
                    $reasonText = Read-Host "Explain why stage '$stage' was rejected"
                    if ([string]::IsNullOrWhiteSpace($reasonText)) {
                        throw "A rejection reason is required."
                    }
                    $quotedReason = $reasonText.Replace("'", "''")
                    Invoke-Expression "$cli reject --project-id $projectId --stage $stage --by operator --reason-code $reasonCode --reason-text '$quotedReason'" | Out-Null
                    throw "Operator rejected gate for stage '$stage'; the decision was recorded."
                } else {
                    throw "Demo stopped by operator after stage '$stage'."
                }
            }
        }
    }

    Write-Host "`nPipeline complete. Project status:"
    Invoke-Expression "$cli status --project-id $projectId"
}
finally {
    Pop-Location
}
