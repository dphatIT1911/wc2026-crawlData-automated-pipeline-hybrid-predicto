import { Injectable } from '@nestjs/common';
import { PrismaService } from './prisma.service';

@Injectable()
export class OddsService {
  constructor(private prisma: PrismaService) {}

  async getLatestOdds() {
    return this.prisma.odds.findMany({
      orderBy: { updatedAt: 'desc' },
      take: 50,
      include: {
        match: {
          include: { homeTeam: true, awayTeam: true }
        }
      }
    });
  }
}
