prod:
	@echo "Setting up production environment..."
	@docker-compose -f docker-compose.yaml up --build
	@echo "Production environment is ready."

dev:
	@echo "Setting up development environment..."
	@docker-compose -f docker-compose.dev.yaml up --build

windows:
	@echo "Setting up for Windows..."
	@docker-compose -f docker-compose.dev-windows.yaml up --build
	@echo "Windows setup completed."

back:
	@echo "Starting backend services..."
	@docker-compose -f docker-compose.back.yaml up --build
	@echo "Backend services are running."
	
all:
	@echo "Please specify a target (prod, dev, windows, back)"