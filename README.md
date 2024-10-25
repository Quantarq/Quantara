What

The functionality allows users to leverage their positions on assets (e.g., ETH) by looping through lending protocols (ZkLend, Nostra) and automated market makers (AMMs). Users deposit collateral into a lending protocol, borrow stablecoins, trade on AMMs, and repeat this loop to increase their holdings. The process allows for up to 5x leverage, providing more utility and liquidity to the DeFi ecosystem. 

Why 

The spot leveraging concept fills a gap in the Starknet ecosystem by enabling users to amplify their positions without the need for perpetual contracts. This improves liquidity and utility for decentralized finance (DeFi) platforms on Starknet, providing a tool that is currently unavailable but highly demanded by users and protocols like ZkLend and Nostra. It allows for stable, long-term leveraged positions at lower costs and risk, which are essential for users aiming to increase exposure without facing the volatility of perpetual contracts. 

How

1. Deposit Collateral: Users deposit assets (e.g., ETH) into a lending protocol like ZkLend or Nostra - interaction with a smart contract on Starknet 
2. Borrow Stablecoins: Users borrow stablecoins (e.g., USDC) against their deposited collateral - The smart contract on Starknet allows users to borrow stablecoins
3. Trading on AMMs: Borrowed stablecoins are swapped for more ETH or the initial asset via AMMs (Starknet-based).
4. Re-Deposit and Re-Borrow: The newly acquired ETH is re-deposited as additional collateral to borrow more stablecoins.
5. Repeating the Loop: This loop repeats, increasing the user's leverage until they reach the desired level or the borrowing limit.


# Development Environment Setup

This guide explains how to start the development environment for the project using Docker Compose. It includes setting up the backend, database, and frontend services.

## Prerequisites

- Docker installed on your machine (v19.03+ recommended).
- Docker Compose installed (v1.27+ recommended).
- Ensure port **5433** is available for the PostgreSQL container.

## Starting the Development Environment

1. **Clone the Repository**

   ```sh
   git clone <repository-url>
   cd <repository-folder>
   ```

2**Build and Start Services**

   To build and run the entire development environment, use the following command:

   ```sh
   docker-compose -f docker-compose.dev.yaml up --build
   ```

   This command will:
   - Build the backend and frontend Docker images.
   - Start the backend, frontend, and PostgreSQL database containers.

3**Access the Application**

   - **Backend API**: Accessible at [http://localhost:8000](http://localhost:8000).
   - **Frontend**: Accessible at [http://localhost:3000](http://localhost:3000).
   - **PostgreSQL Database**: Accessible at `localhost:5433` (make sure to use the `DB_USER` and `DB_PASSWORD` from the `.env.dev` file).

## Common Issues

- **Port Conflict**: Ensure port `5433` is free, as PostgreSQL will bind to this port in the development environment.
- **Docker Build Issues**: If changes in dependencies are not reflected, you may need to clear Docker's cache:

  ```sh
  docker-compose -f docker-compose.dev.yaml build --no-cache
  ```

## Stopping the Development Environment

To stop the environment and remove containers, use:

```sh
docker-compose -f docker-compose.dev.yaml down
```

This command stops all running containers and removes them, but the data volumes will persist.

## Rebuild or Update

If you have made changes to the code or Docker configuration, rebuild the containers:

```sh
docker-compose -f docker-compose.dev.yaml up --build
```

## About Celery

This project utilizes Celery to handle asynchronous tasks. The Celery workers and scheduler are defined within the Docker Compose setup.

### Services Overview

- **Celery Worker**: Executes tasks in the background.
- **Celery Beat**: Schedules periodic tasks.
- **Redis**: Used as the message broker for Celery.

### Running Celery

To start the Celery worker and Celery Beat services, use the following command in the terminal within your project directory:

```bash
docker-compose up -d celery celery_beat
```
### Stopping Celery
To stop the Celery worker and Beat services, run

```bash
docker-compose stop celery celery_beat
```

### Purging Celery Tasks
If you want to purge all tasks from the Celery queue, you can do this by executing

```bash
docker-compose run --rm celery celery -A spotnet_tracker.celery_config purge
```

