import { Controller, Get, Param, ParseIntPipe } from '@nestjs/common';
import { MatchService } from './match.service';

@Controller('matches')
export class MatchController {
  constructor(private readonly matchService: MatchService) {}

  @Get()
  getAllMatches() {
    return this.matchService.getAllMatches();
  }

  @Get(':id')
  getMatchById(@Param('id', ParseIntPipe) id: number) {
    return this.matchService.getMatchById(id);
  }

  @Get(':id/history')
  getMatchHistory(@Param('id', ParseIntPipe) id: number) {
    return this.matchService.getMatchOddsHistory(id);
  }
}
