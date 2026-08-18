import { Module } from '@nestjs/common';
import { ScheduleModule } from '@nestjs/schedule';
import { MatchController } from './match.controller';
import { MatchService } from './match.service';
import { OddsController } from './odds.controller';
import { OddsService } from './odds.service';
import { PrismaService } from './prisma.service';
import { CrawlerService } from './crawler.service';
import { CrawlerController } from './crawler.controller';
import { PredictionController } from './prediction.controller';
import { PredictionService } from './prediction.service';
import { AnalyticsController } from './analytics.controller';
import { AnalyticsService } from './analytics.service';
import { HistoryController } from './history.controller';
import { HistoryService } from './history.service';
import { SettingsController } from './settings.controller';
import { SettingsService } from './settings.service';
import { AppController } from './app.controller';
import { AppService } from './app.service';

@Module({
  imports: [
    ScheduleModule.forRoot()
  ],
  controllers: [
    AppController, 
    MatchController, 
    OddsController, 
    CrawlerController, 
    PredictionController,
    AnalyticsController,
    HistoryController,
    SettingsController
  ],
  providers: [
    AppService, 
    MatchService, 
    OddsService, 
    PrismaService, 
    CrawlerService, 
    PredictionService,
    AnalyticsService,
    HistoryService,
    SettingsService
  ],
})
export class AppModule {}
