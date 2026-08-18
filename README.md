<div align="center">

# ⚽ WC2026 Hybrid Match Predictor

**FIFA World Cup 2026 match outcome prediction system**  
powered by an automated data pipeline and a three-model ensemble AI engine.

[![NestJS](https://img.shields.io/badge/NestJS-11-E0234E?style=flat-square&logo=nestjs&logoColor=white)](https://nestjs.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docs.docker.com/compose/)

</div>

---

## 📌 Overview

This project is a **full-stack sports analytics platform** built around the FIFA World Cup 2026. It ingests live match and betting odds data from multiple sources, stores and transforms them in a relational database, and runs a **hybrid ensemble prediction engine** that combines classical statistics, machine learning, and market intelligence.

**Key capabilities:**

- 🔄 **Automated data pipeline** — scheduled crawlers sync match data and live odds every few hours
- 🧠 **Hybrid AI predictor** — ensemble of Dixon-Coles (MLE), CatBoost (ML), and de-vigged market odds
- 📊 **Analytics dashboard** — visualize team form, head-to-head records, odds movement, and model confidence
- 🧪 **Backtesting framework** — evaluate model accuracy (Brier Score, RPS, Log Loss, ROI simulation) on historical matches

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React / Vite Frontend                    │
│          Dashboard · Predictions · Analytics · History          │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
┌────────────────────────────▼────────────────────────────────────┐
│                      NestJS Backend (Node.js)                   │
│                                                                 │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────────────────┐  │
│  │ CrawlerService│  │  Prediction  │  │  Analytics / History │  │
│  │  (Cron Jobs) │  │  Controller  │  │  Controllers          │  │
│  └──────┬───────┘  └──────┬──────┘  └──────────┬─────────────┘  │
│         │                 │                     │                │
│  ┌──────▼─────────────────▼─────────────────────▼──────────── ┐ │
│  │                 Prisma ORM  ←→  PostgreSQL DB              │ │
│  └────────────────────────────────────────────────────────────┘ │
│         │                 │                                      │
│  ┌──────▼──────┐  ┌───────▼──────────────────────────────────── ┐ │
│  │ API-Football│  │         Python Prediction Engine             │ │
│  │ The Odds API│  │  (FastAPI + Dixon-Coles + CatBoost + Market) │ │
│  └─────────────┘  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Prediction Engine — Hybrid Ensemble

The core of this system is a **three-component ensemble** model, where each component contributes to a weighted final prediction:

| Component | Weight | Description |
|-----------|--------|-------------|
| 🎯 **Dixon-Coles Statistical Model** | 30% | Bivariate Poisson model (Dixon & Coles, 1997). Estimates per-team attack/defense strength via MLE with time-decay weighting. Applies the famous `τ(rho)` correction for low-scoring draw underrepresentation. |
| 📈 **Odds Market Intelligence** | 40% | De-vigs 1X2 market odds (multiplicative method) to extract bookmaker-implied fair probabilities. Tracks odds movement (opening → closing), Closing Line Value (CLV), and sharp money detection. |
| 🌲 **CatBoost ML Model** | 30% | Gradient boosting classifier trained on engineered match features. Degrades gracefully if model artifacts are absent. |

**Why 40% weight on market odds?**  
Empirical research consistently shows betting markets are strong aggregators of information. The ensemble is designed to improve upon the market baseline using statistical and ML signals.

### Feature Engineering (CatBoost input)

Features are organized into 4 groups, computed live from the database before each prediction:

| Group | Features |
|-------|----------|
| **Team Strength** | ELO rating, FIFA ranking, recent form (last 5 matches), goals scored/conceded |
| **Head-to-Head** | H2H win rate, avg goals in H2H, home advantage factor |
| **Market Intelligence** | Fair home/draw/away probability (de-vigged), overround, odds movement magnitude |
| **Match Context** | Tournament stage, neutral venue flag, days since last match |

### Backtesting Metrics

The `Backtester` module evaluates model performance on all finished matches using only pre-match data:

- **Accuracy** — % correct 1X2 predictions
- **Brier Score** — probabilistic calibration (lower = better)
- **Ranked Probability Score (RPS)** — ordered outcome scoring
- **Log Loss** — entropy-based calibration
- **ROI Simulation** — flat-bet strategy return on investment

---

## 📡 Data Pipeline

### Sources

| Source | Data Type | Update Frequency |
|--------|-----------|------------------|
| [API-Football v3](https://www.api-football.com/) | Match fixtures, live scores, team statistics, match events | Cron: 03:00, 12:00, 18:00, 21:00 (ICT) |
| [The Odds API v4](https://the-odds-api.com/) | 1X2 betting odds from 20+ bookmakers | Same schedule as above |

### Crawl Flow

```
Cron Trigger
    ↓
Fetch upcoming WC2026 matches (League ID: 1, Season: 2026)
    ↓
Upsert Tournaments / Teams / Matches → PostgreSQL
    ↓
Fetch live odds for upcoming matches
    ↓
Upsert Odds / OddsHistory (for movement tracking)
    ↓
Fetch match events & stats for live/finished matches
```

---

## 🗄️ Database Schema

Built with **Prisma ORM** on PostgreSQL. Core models:

```
Tournament ──< Match >── Team
                │
         ┌──────┴──────┐
      Odds[]      MatchStats
   OddsHistory[]  MatchEvent[]
   Prediction[]   H2HRecord
                  TeamStats
```

**Notable design decisions:**
- `OddsHistory` stores a full time series of odds for each match — enables CLV and movement analysis
- `H2HRecord` is pre-aggregated to avoid expensive JOIN queries at prediction time
- `TeamStats` stores rolling window stats per team (last N games) for feature engineering

---

## 🖥️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript, Vite, React Router |
| **Backend API** | NestJS 11, TypeScript, `@nestjs/schedule` (cron) |
| **ORM** | Prisma 7 (PostgreSQL adapter) |
| **Database** | PostgreSQL 16 |
| **Prediction Engine** | Python 3.11, FastAPI, SQLAlchemy |
| **ML** | CatBoost, scikit-learn, NumPy, pandas, SciPy |
| **HTTP Client** | Axios (Node), httpx (Python) |
| **Containerization** | Docker, Docker Compose |

---

## 🚀 Getting Started

### Prerequisites

- Node.js 20+, npm
- Python 3.11+, pip
- PostgreSQL 16 (or Docker)
- API keys: [API-Football](https://www.api-football.com/) and [The Odds API](https://the-odds-api.com/)

### 1. Clone & configure

```bash
git clone https://github.com/YOUR_USERNAME/wc2026-hybrid-match-predictor.git
cd wc2026-hybrid-match-predictor
```

### 2. Backend setup

```bash
cd world-cup-odds-backend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API keys and DATABASE_URL

# Run database migrations
npx prisma db push

# Start development server
npm run start:dev
```

### 3. Prediction Engine setup

```bash
cd world-cup-odds-backend/prediction-engine

# Install Python dependencies
pip install -r requirements.txt

# The engine is embedded as a FastAPI app and called by the NestJS backend
# It uses the same DATABASE_URL from the parent .env
```

### 4. Frontend setup

```bash
cd world-cup-odds-frontend

npm install
npm run dev
```

### 5. Docker Compose (recommended)

```bash
# From project root
docker-compose up -d
```

---

## 📁 Project Structure

```
wc2026-hybrid-match-predictor/
├── world-cup-odds-backend/          # NestJS API server
│   ├── src/
│   │   ├── crawler.service.ts       # Data pipeline (API-Football + The Odds API)
│   │   ├── prediction.service.ts    # Bridge to Python engine
│   │   ├── prediction.controller.ts # REST endpoints for predictions
│   │   ├── analytics.service.ts     # Match analytics queries
│   │   ├── history.service.ts       # Historical match data
│   │   └── prisma.service.ts        # DB connection
│   ├── prediction-engine/           # Python AI engine (FastAPI)
│   │   ├── app/
│   │   │   ├── predictor.py         # HybridPredictor — ensemble orchestrator
│   │   │   ├── dixon_coles.py       # Dixon-Coles bivariate Poisson model
│   │   │   ├── odds_analyzer.py     # De-vigging, CLV, market intelligence
│   │   │   ├── features.py          # Feature engineering pipeline
│   │   │   ├── backtest.py          # Backtesting framework
│   │   │   ├── rule_based.py        # Simple rule-based baseline
│   │   │   ├── database.py          # SQLAlchemy session management
│   │   │   └── main.py              # FastAPI app entry point
│   │   ├── fetch_statsbomb.py       # StatsBomb open data loader
│   │   ├── populate_historical.py   # Historical data seeder
│   │   └── requirements.txt
│   ├── prisma/
│   │   └── schema.prisma            # Full database schema
│   ├── Dockerfile
│   └── docker-compose.yml
└── world-cup-odds-frontend/         # React dashboard
    └── src/
        ├── pages/
        │   ├── Dashboard/           # Live match overview
        │   ├── Predictions/         # Model predictions & confidence
        │   ├── Analytics/           # Team & odds analytics
        │   ├── History/             # Past match results
        │   ├── CrawlerData/         # Raw crawled data viewer
        │   └── Settings/            # App configuration
        └── components/
```

---

## 🔌 API Reference

### Prediction Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/prediction/match/:id` | Get hybrid prediction for a match |
| `GET` | `/prediction/upcoming` | Predict all upcoming WC2026 matches |
| `POST` | `/prediction/train` | Trigger CatBoost model re-training |
| `GET` | `/prediction/backtest` | Run backtest on finished matches |
| `GET` | `/prediction/model-metrics` | Get model performance metrics |
| `GET` | `/prediction/team-strengths` | Dixon-Coles attack/defense ratings |
| `GET` | `/prediction/health` | Prediction engine health check |

### Data Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/crawler/status` | Current crawler status |
| `POST` | `/crawler/run` | Manually trigger a crawl |
| `GET` | `/analytics/...` | Match and team analytics |
| `GET` | `/history/...` | Historical match data |

---

## 📚 References

- Dixon, M., & Coles, S. (1997). [Modelling Association Football Scores and Inefficiencies in the Football Betting Market](https://doi.org/10.2307/2986290). *Journal of the Royal Statistical Society*.
- Shin, H. S. (1993). Measuring the incidence of insider trading in a market for state-contingent claims. *The Economic Journal*.
- API-Football Documentation: https://www.api-football.com/documentation-v3
- The Odds API Documentation: https://the-odds-api.com/liveapi/guides/v4/

---

## 📄 License

This project is for educational and portfolio purposes. API data usage is subject to the terms of [API-Football](https://www.api-football.com/terms) and [The Odds API](https://the-odds-api.com/terms).
