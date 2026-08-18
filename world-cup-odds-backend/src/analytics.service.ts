import { Injectable } from '@nestjs/common';
import { PrismaService } from './prisma.service';

@Injectable()
export class AnalyticsService {
  constructor(private prisma: PrismaService) {}

  async getDashboardAnalytics() {
    const totalMatches = await this.prisma.match.count();
    const upcoming = await this.prisma.match.count({ where: { status: 'NS' } });
    const finished = await this.prisma.match.count({ where: { status: 'FT' } });
    const live = await this.prisma.match.count({ where: { status: { in: ['LIVE', 'HT'] } } });

    // Aggregate goals
    const stats = await this.prisma.match.aggregate({
      _sum: {
        homeScore: true,
        awayScore: true,
      },
      where: { status: 'FT' }
    });
    
    const totalGoals = (stats._sum.homeScore || 0) + (stats._sum.awayScore || 0);
    const avgGoals = finished > 0 ? (totalGoals / finished).toFixed(2) : 0;

    // Model Performance
    const modelMetrics = await this.prisma.modelMetrics.findFirst({
      orderBy: { evaluationDate: 'desc' }
    });

    return {
      overview: { totalMatches, upcoming, finished, live },
      goals: { totalGoals, avgGoals },
      aiPerformance: modelMetrics || null
    };
  }
}
