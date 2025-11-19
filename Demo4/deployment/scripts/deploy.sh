#!/bin/bash
# =============================================================================
# AgentManager - Quick Deployment Script
# =============================================================================

set -e

echo "🚀 AgentManager Deployment Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Generate secure tokens
generate_tokens() {
    print_status "Generating secure tokens..."
    
    if command -v python3 &> /dev/null; then
        AUTH_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    elif command -v python &> /dev/null; then
        AUTH_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
        SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
    else
        print_error "Python is required to generate secure tokens"
        exit 1
    fi
    
    print_success "Secure tokens generated"
}

# Setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        cp .env.template .env
        print_success "Created .env file from template"
        
        # Replace tokens in .env file
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/your_secure_server_api_token_here/$AUTH_TOKEN/g" .env
            sed -i '' "s/your_secure_secret_key_here/$SECRET_KEY/g" .env
        else
            # Linux
            sed -i "s/your_secure_server_api_token_here/$AUTH_TOKEN/g" .env
            sed -i "s/your_secure_secret_key_here/$SECRET_KEY/g" .env
        fi
        
        print_warning "Please edit .env file and add your OPENAI_API_KEY and other configuration"
    else
        print_warning ".env file already exists. Skipping creation."
    fi
}

# Deploy server
deploy_server() {
    print_status "Deploying AgentManager Server..."
    
    cd server
    docker-compose up -d --build
    cd ..
    
    print_success "Server deployment started"
    print_status "Waiting for server to be ready..."
    
    # Wait for server to be healthy
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_success "Server is healthy and ready"
            break
        fi
        echo -n "."
        sleep 2
    done
}

# Deploy workers
deploy_workers() {
    print_status "Deploying AgentManager Workers..."
    
    cd worker
    
    # Ask user which workers to deploy
    echo "Select worker deployment mode:"
    echo "1) Individual workers (researcher, analyst, writer)"
    echo "2) Multi-role worker (all capabilities in one container)"
    echo "3) Both individual and multi-role workers"
    read -p "Enter your choice (1-3): " choice
    
    case $choice in
        1)
            docker-compose up -d --build worker-researcher worker-analyst worker-writer
            ;;
        2)
            docker-compose --profile multi-worker up -d --build worker-multi
            ;;
        3)
            docker-compose --profile multi-worker up -d --build
            ;;
        *)
            print_error "Invalid choice. Deploying individual workers by default."
            docker-compose up -d --build worker-researcher worker-analyst worker-writer
            ;;
    esac
    
    cd ..
    print_success "Worker deployment started"
}

# Show deployment status
show_status() {
    print_status "Deployment Status:"
    echo ""
    
    print_status "Server containers:"
    cd server && docker-compose ps && cd ..
    
    echo ""
    print_status "Worker containers:"
    cd worker && docker-compose ps && cd ..
    
    echo ""
    print_status "Available endpoints:"
    echo "  🌐 Server API: http://localhost:8000"
    echo "  📚 API Docs: http://localhost:8000/docs"
    echo "  ❤️ Health Check: http://localhost:8000/health"
    echo ""
    print_status "Worker metrics:"
    echo "  📊 Researcher: http://localhost:8081"
    echo "  📊 Analyst: http://localhost:8082"
    echo "  📊 Writer: http://localhost:8083"
    echo "  📊 Multi-role: http://localhost:8084"
}

# Main deployment flow
main() {
    print_status "Starting AgentManager deployment..."
    
    # Check requirements
    check_docker
    
    # Generate tokens
    generate_tokens
    
    # Setup environment
    setup_environment
    
    # Create necessary directories
    mkdir -p logs temp config
    
    # Check if OPENAI_API_KEY is set
    if ! grep -q "your_openai_api_key_here" .env; then
        print_warning "Remember to set your OPENAI_API_KEY in .env file"
        read -p "Press Enter to continue after setting up .env file..."
    fi
    
    # Deploy server first
    deploy_server
    
    # Deploy workers
    deploy_workers
    
    # Show status
    show_status
    
    print_success "🎉 AgentManager deployment completed!"
    print_status "You can now submit tasks to: http://localhost:8000/v1/tasks"
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        print_status "Stopping all AgentManager services..."
        cd server && docker-compose down
        cd ../worker && docker-compose down
        print_success "All services stopped"
        ;;
    "restart")
        print_status "Restarting all AgentManager services..."
        cd server && docker-compose restart
        cd ../worker && docker-compose restart
        print_success "All services restarted"
        ;;
    "logs")
        print_status "Showing logs for all services..."
        cd server && docker-compose logs -f &
        cd ../worker && docker-compose logs -f &
        wait
        ;;
    "status")
        show_status
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|logs|status}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Deploy AgentManager server and workers"
        echo "  stop    - Stop all AgentManager services"
        echo "  restart - Restart all AgentManager services"
        echo "  logs    - Show logs from all services"
        echo "  status  - Show current deployment status"
        exit 1
        ;;
esac