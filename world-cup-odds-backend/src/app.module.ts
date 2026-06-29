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
import { AppController } from './app.controller';
import { AppService } from './app.service';

@Module({
  imports: [
    ScheduleModule.forRoot()
  ],
  controllers: [AppController, MatchController, OddsController, CrawlerController, PredictionController],
  providers: [AppService, MatchService, OddsService, PrismaService, CrawlerService, PredictionService],
})
export class AppModule {}
