import { Injectable } from '@nestjs/common';
import { PrismaService } from './prisma.service';

@Injectable()
export class MatchService {
  constructor(private prisma: PrismaService) {}

  async getAllMatches() {
    return this.prisma.match.findMany({
      where: {
        tournament: { name: 'World Cup 2026' }
      },
      include: {
        homeTeam: true,
        awayTeam: true,
        tournament: true,
      },
      orderBy: { startTime: 'asc' },
    });
  }

  async getMatchById(id: number) {
    return this.prisma.match.findUnique({
      where: { id },
      include: {
        homeTeam: true,
        awayTeam: true,
        odds: true,
      },
    });
  }

  async getMatchOddsHistory(matchId: number) {
    return this.prisma.oddsHistory.findMany({
      where: { matchId },
      orderBy: { createdAt: 'desc' },
    });
  }
}
