import { Controller, Get, Post, Param, ParseIntPipe, HttpException, HttpStatus, Query } from '@nestjs/common';
import { PredictionService } from './prediction.service';

@Controller('prediction')
export class PredictionController {
  constructor(private readonly predictionService: PredictionService) {}

  /**
   * GET /prediction/match/:id?modelType=hybrid|rule_based
   * Get prediction for a specific match.
   */
  @Get('match/:id')
  async predictMatch(
    @Param('id', ParseIntPipe) id: number,
    @Query('modelType') modelType?: string,
  ) {
    try {
      return await this.predictionService.predictMatch(id, modelType);
    } catch (error) {
      throw new HttpException(
        { message: 'Prediction service error', error: error.message },
        HttpStatus.SERVICE_UNAVAILABLE,
      );
    }
  }

  /**
   * GET /prediction/upcoming?modelType=hybrid|rule_based
   * Get predictions for all upcoming matches.
   */
  @Get('upcoming')
  async predictUpcoming(@Query('modelType') modelType?: string) {
    try {
      return await this.predictionService.predictUpcoming(modelType);
    } catch (error) {
      throw new HttpException(
        { message: 'Prediction service error', error: error.message },
        HttpStatus.SERVICE_UNAVAILABLE,
      );
    }
  }

  /**
   * POST /prediction/train
   * Trigger model training (admin only).
   */
  @Post('train')
  async trainModels() {
    try {
      return await this.predictionService.trainModels();
    } catch (error) {
      throw new HttpException(
        { message: 'Training failed', error: error.message },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  /**
   * GET /prediction/backtest
   * Run backtest on finished matches.
   */
  @Get('backtest')
  async runBacktest() {
    try {
      return await this.predictionService.runBacktest();
    } catch (error) {
      throw new HttpException(
        { message: 'Backtest failed', error: error.message },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  /**
   * GET /prediction/model-metrics
   * Get model performance metrics.
   */
  @Get('model-metrics')
  async getModelMetrics() {
    try {
      return await this.predictionService.getModelMetrics();
    } catch (error) {
      throw new HttpException(
        { message: 'Metrics unavailable', error: error.message },
        HttpStatus.SERVICE_UNAVAILABLE,
      );
    }
  }

  /**
   * GET /prediction/team-strengths
   * Get team attack/defense ratings.
   */
  @Get('team-strengths')
  async getTeamStrengths() {
    try {
      return await this.predictionService.getTeamStrengths();
    } catch (error) {
      throw new HttpException(
        { message: 'Team strengths unavailable', error: error.message },
        HttpStatus.SERVICE_UNAVAILABLE,
      );
    }
  }

  /**
   * GET /prediction/health
   * Check prediction engine health.
   */
  @Get('health')
  async healthCheck() {
    const isHealthy = await this.predictionService.healthCheck();
    return {
      prediction_engine: isHealthy ? 'UP' : 'DOWN',
      timestamp: new Date().toISOString(),
    };
  }
}
