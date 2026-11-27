param(
    [string]$BaseUrl = "http://localhost:5000"
)
$ErrorActionPreference = "Stop"

function Test-Endpoint([string]$Name, [string]$Url) {
    Write-Host "Testing $Name ..." -ForegroundColor Cyan
    $result = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 20
    if ($null -eq $result) { throw "$Name returned an empty response." }
    Write-Host "PASS $Name" -ForegroundColor Green
    return $result
}

$health = Test-Endpoint "health" "$BaseUrl/api/v1/system/health"
if ($health.status -ne "healthy") { throw "Health endpoint did not return healthy." }

$ready = Test-Endpoint "database readiness" "$BaseUrl/api/v1/system/ready"
if ($ready.status -ne "ready") { throw "Database is not ready." }

$categories = Test-Endpoint "categories" "$BaseUrl/api/v1/catalog/categories"
if (($categories.categories | Measure-Object).Count -lt 1) { throw "No categories returned. Run the catalog seed SQL." }

$products = Test-Endpoint "products" "$BaseUrl/api/v1/catalog/products?page=1&pageSize=12"
if ($products.totalItems -lt 1) { throw "No products returned. Run the catalog seed SQL." }
if (($products.items | Measure-Object).Count -lt 1) { throw "Product page is empty." }

$id = $products.items[0].id
$detail = Test-Endpoint "product detail" "$BaseUrl/api/v1/catalog/products/$id"
if ($detail.product.id -ne $id) { throw "Product detail ID mismatch." }

Write-Host "All FINMARKET catalog smoke tests passed." -ForegroundColor Green
