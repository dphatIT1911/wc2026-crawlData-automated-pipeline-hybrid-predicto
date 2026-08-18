import { Injectable } from '@nestjs/common';
import { PrismaService } from './prisma.service';

@Injectable()
export class HistoryService {
  constructor(private prisma: PrismaService) {}

  async getCrawlerLogs(limit: number = 20) {
    return this.prisma.crawlerLog.findMany({
      orderBy: { runAt: 'desc' },
      take: limit,
    });
  }

  async getOddsHistory(limit: number = 20) {
    return this.prisma.oddsHistory.findMany({
      orderBy: { createdAt: 'desc' },
      take: limit,
      include: {
        match: {
          include: {
            homeTeam: true,
            awayTeam: true,
          }
        }
      }
    });
  }
}
