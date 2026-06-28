import { Injectable, Logger } from '@nestjs/common';
import axios from 'axios';

@Injectable()
export class PredictionService {
  private readonly logger = new Logger(PredictionService.name);
  private readonly PREDICTION_ENGINE_URL = process.env.PREDICTION_ENGINE_URL || 'http://localhost:8000';

  /**
   * Get prediction for a specific match from Python prediction engine.
   */
  async predictMatch(matchId: number, modelType: string = 'hybrid') {
    try {
      const resp = await axios.get(`${this.PREDICTION_ENGINE_URL}/prediction/match/${matchId}`, {
        params: { model_type: modelType },
        timeout: 30000,
      });
      return resp.data;
    } catch (error) {
      this.logger.error(`Failed to get prediction for match ${matchId}: ${error.message}`);
      throw new Error(`Prediction service unavailable: ${error.message}`);
    }
  }

  /**
   * Get predictions for all upcoming matches.
   */
  async predictUpcoming(modelType: string = 'hybrid') {
    try {
      const resp = await axios.get(`${this.PREDICTION_ENGINE_URL}/prediction/upcoming`, {
        params: { model_type: modelType },
        timeout: 60000,
      });
      return resp.data;
    } catch (error) {
      this.logger.error(`Failed to get upcoming predictions: ${error.message}`);
      throw new Error(`Prediction service unavailable: ${error.message}`);
    }
  }

  /**
   * Trigger model training.
   */
  async trainModels() {
    try {
      const resp = await axios.post(`${this.PREDICTION_ENGINE_URL}/prediction/train`, {}, {
        timeout: 120000, // Training can take a while
      });
      return resp.data;
    } catch (error) {
      this.logger.error(`Failed to train models: ${error.message}`);
      throw new Error(`Training failed: ${error.message}`);
    }
  }

  /**
   * Run backtest on finished matches.
   */
  async runBacktest() {
    try {
      const resp = await axios.get(`${this.PREDICTION_ENGINE_URL}/prediction/backtest`, {
        timeout: 120000,
      });
      return resp.data;
    } catch (error) {
      this.logger.error(`Backtest failed: ${error.message}`);
      throw new Error(`Backtest failed: ${error.message}`);
    }
  }

  /**
   * Get model performance metrics.
   */
  async getModelMetrics() {
    try {
      const resp = await axios.get(`${this.PREDICTION_ENGINE_URL}/prediction/model-metrics`, {
        timeout: 10000,
      });
      return resp.data;
    } catch (error) {
      this.logger.error(`Failed to get model metrics: ${error.message}`);
      throw new Error(`Metrics unavailable: ${error.message}`);
    }
  }

  /**
   * Get team strength ratings from Dixon-Coles model.
   */
  async getTeamStrengths() {
    try {
      const resp = await axios.get(`${this.PREDICTION_ENGINE_URL}/prediction/team-strengths`, {
        timeout: 10000,
      });
      return resp.data;
    } catch (error) {
      this.logger.error(`Failed to get team strengths: ${error.message}`);
      throw new Error(`Team strengths unavailable: ${error.message}`);
    }
  }

  /**
   * Check if prediction engine is healthy.
   */
  async healthCheck(): Promise<boolean> {
    try {
      const resp = await axios.get(`${this.PREDICTION_ENGINE_URL}/ping`, {
        timeout: 5000,
      });
      return resp.data === 'OK';
    } catch {
      return false;
    }
  }
}
