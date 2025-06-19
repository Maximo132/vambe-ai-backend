# Script para verificar la estructura del proyecto
Write-Host "Verificando estructura del proyecto..." -ForegroundColor Cyan

# Función para mostrar la estructura de directorios
function Show-Tree {
    param(
        [string]$path = ".",
        [string]$indent = "",
        [switch]$isLast
    )
    
    $current = Get-Item $path
    $name = $current.Name
    
    if ($indent -eq "") {
        Write-Host "$name" -ForegroundColor Green
    } else {
        $marker = if ($isLast) { "└──" } else { "├──" }
        Write-Host "$indent$marker $name" -ForegroundColor Green
    }
    
    if ($current.PSIsContainer) {
        $items = @(Get-ChildItem -Path $path -Force | Sort-Object { $_.PSIsContainer })
        $count = $items.Count
        
        for ($i = 0; $i -lt $count; $i++) {
            $item = $items[$i]
            $newIndent = if ($isLast) { $indent + "    " } else { $indent + "│   " }
            Show-Tree -path $item.FullName -indent $newIndent -isLast:($i -eq $count - 1)
        }
    }
}

# Mostrar estructura de directorios
Write-Host "`nEstructura del proyecto:" -ForegroundColor Yellow
Show-Tree -path "."

# Verificar archivos importantes
Write-Host "`nVerificando archivos importantes..." -ForegroundColor Yellow
$requiredFiles = @(
    "src/app/__init__.py",
    "src/app/db/__init__.py",
    "src/app/db/base.py",
    "src/app/models/__init__.py",
    "src/app/models/base.py",
    "alembic.ini",
    "migrations/env.py"
)

foreach ($file in $requiredFiles) {
    $exists = Test-Path -Path $file
    $status = if ($exists) { "✓" } else { "✗" }
    $color = if ($exists) { "Green" } else { "Red" }
    Write-Host "$status $file" -ForegroundColor $color
}

# Verificar importaciones de Python
Write-Host "`nVerificando importaciones de Python..." -ForegroundColor Yellow
try {
    $env:PYTHONPATH = ";$pwd\src"
    $result = python -c "import sys; print('Python Path:'); [print(p) for p in sys.path]; from app.db import base; print('✓ app.db.base importado correctamente')" 2>&1
    Write-Host $result -ForegroundColor Green
} catch {
    Write-Host "Error al verificar importaciones: $_" -ForegroundColor Red
}

Write-Host "`nVerificación completada." -ForegroundColor Cyan
