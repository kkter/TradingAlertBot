# Crypto Trading Alert Bot

A Python-based bot that monitors cryptocurrency markets on the Binance exchange and sends timely alerts to a Telegram chat for specific trading signals.

## Features

- **Multi-Symbol & Multi-Timeframe Monitoring**: Easily configure which trading pairs and timeframes (e.g., 4h, 1d, 1w) to analyze in `config.py`.
- **Two Core Strategies**:
    1.  **Oversold/Overbought Strategy**: Uses a combination of RSI, Bollinger Bands, and MACD to identify potential market reversals. It can send alerts for individual indicator signals or for a stronger "combined signal" when at least two indicators agree.
    2.  **EMA Breakthrough Strategy**: Detects when the price crosses above (breakout) or below (breakdown) key Exponential Moving Averages (21, 55, 100), signaling potential trend changes.
- **Telegram Notifications**: Delivers well-formatted, easy-to-read alerts directly to your specified Telegram chat, complete with emojis to signify the signal's nature and importance.
- **Highly Configurable**: All critical parameters, including symbols, indicator settings (RSI period, MACD values, etc.), and EMA periods, are centralized in `config.py` for easy modification.
- **Scheduled Analysis**: Runs analysis jobs automatically at regular intervals (default is hourly).
- **Docker Support**: Comes with `Dockerfile` and `docker-compose.yml` for straightforward, containerized deployment.

## Project Structure

```
.
├── main.py                     # Main application entry point
├── config.py                   # Central configuration for symbols and parameters
├── oversold_overbought_strategy.py # Logic for RSI, BBands, and MACD analysis
├── ema_strategy.py             # Logic for EMA breakthrough analysis
├── telegram_bot.py             # Handles all Telegram bot interactions
├── requirements.txt            # Python dependencies
├── .env.example                # Example for environment variables
├── Dockerfile                  # Docker image definition
└── docker-compose.yml          # Docker Compose configuration
```

## Local Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:kkter/TradingAlertBot.git
    cd TradingAlertBot
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    -   Rename `.env.example` to `.env`.
    -   Obtain a bot token from Telegram's [BotFather](https://t.me/BotFather).
    -   Find your personal `Chat ID` by messaging a bot like `@userinfobot`.
    -   Fill in the `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in your new `.env` file.

5.  **Customize Configuration (Optional):**
    -   Modify `config.py` to change the symbols to monitor, timeframe parameters, or EMA periods.

6.  **Run the bot:**
    ```bash
    python main.py
    ```

## Docker Deployment

Deploy the bot easily using Docker and Docker Compose.

1.  **Prerequisites**:
    -   [Docker](https://www.docker.com/get-started) installed.
    -   [Docker Compose](https://docs.docker.com/compose/install/) installed.

2.  **Environment File**:
    -   Create a `.env` file in the project root (same directory as `docker-compose.yml`).
    -   Add your Telegram credentials to this file:
        ```
        TELEGRAM_BOT_TOKEN=your_bot_token_here
        TELEGRAM_CHAT_ID=your_chat_id_here
        ```

3.  **Build and Run**:
    -   Open a terminal in the project's root directory and run the following command to build the image and start the container in detached mode:
        ```bash
        docker-compose up --build -d
        ```

4.  **Manage the Bot**:
    -   **Check logs**:
        ```bash
        docker-compose logs -f
        ```
    -   **Stop the bot**:
        ```bash
        docker-compose down
        ```