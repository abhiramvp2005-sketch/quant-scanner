# Quant Scanner: Asynchronous Algorithmic Trading Engine

A high-performance, asynchronous market-scanning engine designed to execute a quantitative trend-following strategy with sub-second latency. Built in Python, this engine evaluates live cryptocurrency and forex market data, identifies structural pullback setups, and pushes real-time execution alerts.

## Core Features

- **Sniper Entry Logic:** Evaluates complex candlestick morphometrics (pinbars, engulfing patterns, wick-to-body ratios) exactly at candle close to eliminate lag and maximize Risk-to-Reward (R\:R) expectancy.
- **Asynchronous Data Ingestion:** Utilizes `asyncio` and the `ccxt` library for non-blocking REST polling and WebSocket streaming, enabling multi-asset scalability without thread blocking.
- **Network Resilience:** Integrates strict API rate-limit management and exponential backoff protocols (`tenacity`) to gracefully handle dropped packets and prevent WAF-triggered IP bans.
- **Proprietary Visual Indicators:** Includes custom Indie v5 scripts tailored for the Exness platform to visually cross-verify structural market signals against decentralized broker tick feeds.
- **Cloud-Native Deployment:** Optimized for Oracle Cloud Infrastructure (OCI) Linux virtual machines to establish low-latency regional connectivity and bypass PaaS geographical API blocks.

## System Architecture & Tech Stack

- **Language:** Python 3.10+
- **Libraries:** Pandas, CCXT, Asyncio, Tenacity, Logging
- **Infrastructure:** Oracle Cloud Infrastructure (OCI), Linux, Git
- **Custom Scripting:** Exness Indie Script (v5)

## Quantitative Strategy: EMA Pullback Rejection

The engine executes a rigid trend-continuation system aiming for a 3:1 Risk-to-Reward profile.

1. **Macro Trend Regime:** Validates directional momentum using the 200-period Exponential Moving Average (EMA).
2. **Dynamic Support/Resistance:** Identifies structural pullbacks touching the 10-period EMA.
3. **Candlestick Morphometrics:** Requires precise rejection signatures, calculating upper/lower wick ratios (e.g., wick must represent $\ge$ 35% of the total candle range) to confirm institutional defense of the EMA.
4. **Volume & Momentum Filters:** Suppresses signals during sideways consolidation using volume moving averages (VMA) and prevents entries on overextended mean-reversion anomalies using ATR bounds.

## Project Structure

Plaintext

```
quant-scanner/
├── src/
│   ├── main.py                 # Application entry point and orchestrator
│   ├── data_ingestion.py       # Async CCXT exchange connections and rate limiting
│   ├── strategy_engine.py      # Pandas-based quantitative logic and signal generation
│   └── alerts.py               # Telegram bot integration for real-time signaling
├── indicators/
│   └── exness_sniper_ema.py    # Custom Indie v5 script for Exness visualization
├── .env                        # Private credentials (ignored by Git)
├── .gitignore                  # Git tracking rules
├── requirements.txt            # Python dependencies
└── README.md

```

## Installation & Setup

# Quant Scanner: Asynchronous Algorithmic Trading Engine

A high-performance, asynchronous market-scanning engine designed to execute a quantitative trend-following strategy with sub-second latency. Built in Python, this engine evaluates live cryptocurrency and forex market data, identifies structural pullback setups, and pushes real-time execution alerts.

## Core Features

- **Sniper Entry Logic:** Evaluates complex candlestick morphometrics (pinbars, engulfing patterns, wick-to-body ratios) exactly at candle close to eliminate lag and maximize Risk-to-Reward (R\:R) expectancy.
- **Asynchronous Data Ingestion:** Utilizes `asyncio` and the `ccxt` library for non-blocking REST polling and WebSocket streaming, enabling multi-asset scalability without thread blocking.
- **Network Resilience:** Integrates strict API rate-limit management and exponential backoff protocols (`tenacity`) to gracefully handle dropped packets and prevent WAF-triggered IP bans.
- **Proprietary Visual Indicators:** Includes custom Indie v5 scripts tailored for the Exness platform to visually cross-verify structural market signals against decentralized broker tick feeds.
- **Cloud-Native Deployment:** Optimized for Oracle Cloud Infrastructure (OCI) Linux virtual machines to establish low-latency regional connectivity and bypass PaaS geographical API blocks.

## System Architecture & Tech Stack

- **Language:** Python 3.10+
- **Libraries:** Pandas, CCXT, Asyncio, Tenacity, Logging
- **Infrastructure:** Oracle Cloud Infrastructure (OCI), Linux, Git
- **Custom Scripting:** Exness Indie Script (v5)

## Quantitative Strategy: EMA Pullback Rejection

The engine executes a rigid trend-continuation system aiming for a 3:1 Risk-to-Reward profile.

1. **Macro Trend Regime:** Validates directional momentum using the 200-period Exponential Moving Average (EMA).
2. **Dynamic Support/Resistance:** Identifies structural pullbacks touching the 10-period EMA.
3. **Candlestick Morphometrics:** Requires precise rejection signatures, calculating upper/lower wick ratios (e.g., wick must represent $\ge$ 35% of the total candle range) to confirm institutional defense of the EMA.
4. **Volume & Momentum Filters:** Suppresses signals during sideways consolidation using volume moving averages (VMA) and prevents entries on overextended mean-reversion anomalies using ATR bounds.

## Project Structure

Plaintext

```
quant-scanner/
├── src/
│   ├── main.py                 # Application entry point and orchestrator
│   ├── data_ingestion.py       # Async CCXT exchange connections and rate limiting
│   ├── strategy_engine.py      # Pandas-based quantitative logic and signal generation
│   └── alerts.py               # Telegram bot integration for real-time signaling
├── indicators/
│   └── exness_sniper_ema.py    # Custom Indie v5 script for Exness visualization
├── .env                        # Private credentials (ignored by Git)
├── .gitignore                  # Git tracking rules
├── requirements.txt            # Python dependencies
└── README.md

```

## Installation & Setup

1. **Clone the repository:**

   Bash
   ```
   git clone https://github.com/YourUsername/quant-scanner.git
   cd quant-scanner

   ```
2. **Initialize a virtual environment:**

   Bash
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate

   ```
3. **Install dependencies:**

   Bash
   ```
   pip install -r requirements.txt

   ```
4. **Configure Environment Variables:**

   Create a `.env` file in the root directory and add your API credentials:

   Code snippet
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   # Add exchange API keys here if executing live trades
   ```

1) **Clone the repository:**

   Bash
   ```
   git clone https://github.com/YourUsername/quant-scanner.git
   cd quant-scanner

   ```
2) **Initialize a virtual environment:**

   Bash
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate

   ```
3) **Install dependencies:**

   Bash
   ```
   pip install -r requirements.txt

   ```
4) **Configure Environment Variables:**

   Create a `.env` file in the root directory and add your API credentials:

   Code snippet
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   # Add exchange API keys here if executing live trades
   ```

