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

@Module({
  imports: [
    ScheduleModule.forRoot()
  ],
  controllers: [MatchController, OddsController, CrawlerController, PredictionController],
  providers: [MatchService, OddsService, PrismaService, CrawlerService, PredictionService],
})
export class AppModule {}
