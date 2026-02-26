@echo off
REM SoulSync Build and Deployment Script for Windows
REM Handles building Docker image and deploying to Docker Hub

setlocal enabledelayedexpansion

REM Configuration
set DOCKER_USERNAME=boulderbadgedad
set IMAGE_NAME=soulsync
set IMAGE_TAG=%1
if "%IMAGE_TAG%"=="" set IMAGE_TAG=latest
set REGISTRY=%DOCKER_USERNAME%/%IMAGE_NAME%

REM Colors (using chcp 65001 for Unicode)
chcp 65001 >nul 2>&1
set GREEN=[92m
set RED=[91m
set YELLOW=[93m
set BLUE=[94m
set NC=[0m

REM Helper functions
:print_header
echo.
echo %BLUE%================================%NC%
echo %BLUE%%~1%NC%
echo %BLUE%================================%NC%
echo.
goto :eof

:print_success
echo %GREEN%OK: %~1%NC%
goto :eof

:print_error
echo %RED%ERROR: %~1%NC%
goto :eof

:print_warning
echo %YELLOW%WARNING: %~1%NC%
goto :eof

:verify_docker
call :print_header "Verifying Docker Installation"

docker --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Docker is not installed or not in PATH"
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Docker Compose is not installed or not in PATH"
    exit /b 1
)

call :print_success "Docker and Docker Compose found"
docker --version
docker-compose --version
goto :eof

:run_tests
call :print_header "Running Tests"

where pytest >nul 2>&1
if errorlevel 1 (
    call :print_warning "pytest not installed, skipping tests"
    call :print_warning "To run tests: pip install pytest && pytest tests/core/ -q"
    goto :eof
)

call :print_warning "Running test suite..."
pytest tests/core/ -q
if errorlevel 1 (
    call :print_error "Tests failed"
    exit /b 1
)

call :print_success "All tests passed"
goto :eof

:build_image
call :print_header "Building Docker Image"

if not exist "Dockerfile" (
    call :print_error "Dockerfile not found in current directory"
    exit /b 1
)

call :print_warning "Building image: %REGISTRY%:%IMAGE_TAG%"

docker build -t "%REGISTRY%:%IMAGE_TAG%" .
if errorlevel 1 (
    call :print_error "Failed to build Docker image"
    exit /b 1
)

call :print_success "Docker image built successfully"
docker images | findstr "%REGISTRY%"

REM Also tag as latest if not already latest
if not "%IMAGE_TAG%"=="latest" (
    docker tag "%REGISTRY%:%IMAGE_TAG%" "%REGISTRY%:latest"
    call :print_success "Tagged as latest"
)
goto :eof

:test_image_locally
call :print_header "Testing Docker Image Locally"

call :print_warning "Starting container for testing..."

REM Create temp directories for testing
if not exist "test-data\data" mkdir test-data\data
if not exist "test-data\logs" mkdir test-data\logs
if not exist "test-data\downloads" mkdir test-data\downloads

REM Run container with test volumes
docker run -d ^
    --name soulsync-test ^
    -p 8008:8008 ^
    -v "%cd%\test-data\data:/data" ^
    -v "%cd%\test-data\logs:/app/logs" ^
    -v "%cd%\test-data\downloads:/app/downloads" ^
    -e FLASK_ENV=production ^
    "%REGISTRY%:%IMAGE_TAG%"

if errorlevel 1 (
    call :print_error "Failed to start test container"
    exit /b 1
)

call :print_success "Container started"

REM Wait for container to be healthy
call :print_warning "Waiting for container to be ready (30 seconds)..."
timeout /t 30 /nobreak

REM Check if container is still running
docker ps | findstr soulsync-test >nul 2>&1
if errorlevel 1 (
    call :print_error "Container stopped"
    docker logs soulsync-test
    exit /b 1
)

call :print_success "Container is running"

REM Clean up test container
call :print_warning "Cleaning up test container..."
docker stop soulsync-test >nul 2>&1
docker rm soulsync-test >nul 2>&1
rmdir /s /q test-data >nul 2>&1

call :print_success "Image testing complete"
goto :eof

:docker_login
call :print_header "Docker Hub Authentication"

docker ps >nul 2>&1
if not errorlevel 1 (
    call :print_success "Already authenticated with Docker"
    goto :eof
)

call :print_warning "Please log in to Docker Hub"
docker login
goto :eof

:push_image
call :print_header "Pushing Image to Docker Hub"

call :print_warning "Pushing %REGISTRY%:%IMAGE_TAG%..."

docker push "%REGISTRY%:%IMAGE_TAG%"
if errorlevel 1 (
    call :print_error "Failed to push image"
    exit /b 1
)

call :print_success "Image pushed successfully"
echo.
echo Image available at: https://hub.docker.com/r/%REGISTRY%/tags
goto :eof

:show_deployment_instructions
call :print_header "Deployment Instructions"

echo.
echo %GREEN%OK: Build and push completed successfully!%NC%
echo.
echo To deploy the application:
echo.
echo %YELLOW%Option 1: Using docker-compose (Recommended)%NC%
echo   1. Create data directories:
echo      mkdir data logs downloads
echo.
echo   2. Update docker-compose.yml if needed
echo.
echo   3. Start the application:
echo      docker-compose up -d
echo.
echo   4. Access at: http://localhost:8008
echo.
echo %YELLOW%Option 2: Direct docker run%NC%
echo   docker run -d ^^
echo     --name soulsync-webui ^^
echo     -p 8008:8008 ^^
echo     -v %%cd%%\data:/data ^^
echo     -v %%cd%%\logs:/app/logs ^^
echo     -v %%cd%%\downloads:/app/downloads ^^
echo     -e FLASK_ENV=production ^^
echo     %REGISTRY%:%IMAGE_TAG%
echo.
echo %YELLOW%Useful Commands%NC%
echo   View logs:
echo     docker-compose logs -f soulsync
echo.
echo   Check health:
echo     docker-compose ps
echo.
echo   Stop:
echo     docker-compose down
echo.
echo %YELLOW%Secrets Management%NC%
echo   Your credentials are now stored encrypted in the database!
echo.
echo   Security best practices:
echo   - Never commit config/.encryption_key to git
echo   - Backup database/config.db and config/.encryption_key
echo   - Use HTTPS in production (with reverse proxy)
echo.
echo For more details, see BUILD_AND_DEPLOY.md
echo.
goto :eof

:main_menu
call :print_header "SoulSync Build and Deployment"

echo.
echo Select action:
echo   1) Build Docker image (local testing only)
echo   2) Build and test Docker image locally
echo   3) Build, test, and push to Docker Hub
echo   4) Just test existing image
echo   5) Show deployment instructions
echo   6) Exit
echo.

set /p choice="Enter choice [1-6]: "

if "%choice%"=="1" (
    call :verify_docker
    call :build_image
    call :show_deployment_instructions
) else if "%choice%"=="2" (
    call :verify_docker
    call :run_tests
    call :build_image
    call :test_image_locally
    call :show_deployment_instructions
) else if "%choice%"=="3" (
    call :verify_docker
    call :run_tests
    call :build_image
    call :test_image_locally
    call :docker_login
    call :push_image
    call :show_deployment_instructions
) else if "%choice%"=="4" (
    call :verify_docker
    call :test_image_locally
) else if "%choice%"=="5" (
    call :show_deployment_instructions
) else if "%choice%"=="6" (
    call :print_success "Exiting"
    exit /b 0
) else (
    call :print_error "Invalid choice"
    call :main_menu
)
goto :eof

REM Main script
setlocal enabledelayedexpansion

REM Check if we're in the SoulSync directory
if not exist "Dockerfile" (
    call :print_error "This script must be run from the SoulSync root directory"
    exit /b 1
)

if not exist "web_server.py" (
    call :print_error "This script must be run from the SoulSync root directory"
    exit /b 1
)

REM If arguments provided, run non-interactive mode
if "%~1"=="" (
    call :main_menu
) else if "%~1"=="build" (
    call :verify_docker
    call :build_image
) else if "%~1"=="test" (
    call :verify_docker
    call :test_image_locally
) else if "%~1"=="push" (
    call :verify_docker
    call :build_image
    call :docker_login
    call :push_image
) else (
    echo Usage: %0 [build^|test^|push]
    exit /b 1
)

endlocal
