import { Controller, Get, Query } from '@nestjs/common';
import { HistoryService } from './history.service';

@Controller('history')
export class HistoryController {
  constructor(private readonly historyService: HistoryService) {}

  @Get('crawler')
  getCrawlerLogs(@Query('limit') limit?: string) {
    return this.historyService.getCrawlerLogs(limit ? parseInt(limit, 10) : 20);
  }

  @Get('odds')
  getOddsHistory(@Query('limit') limit?: string) {
    return this.historyService.getOddsHistory(limit ? parseInt(limit, 10) : 20);
  }
}
