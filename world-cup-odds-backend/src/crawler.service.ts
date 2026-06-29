import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { PrismaService } from './prisma.service';
import axios from 'axios';

@Injectable()
export class CrawlerService implements OnModuleInit {
  private readonly logger = new Logger(CrawlerService.name);
  
  // API-Football Config
  private readonly API_FOOTBALL_KEY = process.env.API_FOOTBALL_KEY || 'test-key';
  private readonly API_FOOTBALL_URL = 'https://v3.football.api-sports.io';
  private readonly WC_LEAGUE_ID = 1; // FIFA World Cup
  private readonly SEASON = 2026;

  // The Odds API Config
  private readonly THE_ODDS_API_KEY = process.env.THE_ODDS_API_KEY || 'test-key';
  private readonly THE_ODDS_API_URL = 'https://api.the-odds-api.com/v4/sports';
  private readonly SPORT_KEY = 'soccer_fifa_world_cup'; // FIFA World Cup

  private isCrawling = false;

  constructor(private prisma: PrismaService) {}

  // Auto-run crawler on startup to ensure fresh data (run in background)
  async onModuleInit() {
    this.logger.log('Backend started! Running initial data crawl in background...');
    this.crawlMatchesAndOdds()
      .then(() => this.logger.log('Initial crawl completed successfully.'))
      .catch(error => this.logger.error('Initial crawl failed:', error));
  }

  @Cron('0 3,12,18,21 * * *', { timeZone: 'Asia/Ho_Chi_Minh' })
  async handleCron() {
    if (this.isCrawling) {
      this.logger.warn('Crawler is already running. Skipping this schedule.');
      return;
    }
    
    this.isCrawling = true;
    this.logger.log('Starting scheduled crawling (3:00, 12:00, 18:00, 21:00)...');
    const startTime = Date.now();
    let crawlerLog = { matches: 0, odds: 0, changes: 0, status: 'SUCCESS', error: null };
    
    try {
      crawlerLog = await this.crawlMatchesAndOdds();
    } catch (error) {
      crawlerLog.status = 'FAILED';
      crawlerLog.error = error.message;
      this.logger.error('Failed to crawl data', error);
    }

    // Save crawler log
    try {
      await this.prisma.crawlerLog.create({
        data: {
          status: crawlerLog.status,
          matches: crawlerLog.matches,
          odds: crawlerLog.odds,
          changes: crawlerLog.changes,
          error: crawlerLog.error,
        }
      });
    } catch (e) {
      this.logger.error('Failed to save crawler log', e.message);
    }

    this.isCrawling = false;
    this.logger.log(`Crawl finished in ${Date.now() - startTime}ms`);
  }

  async crawlMatchesAndOdds() {
    const result = { matches: 0, odds: 0, changes: 0, status: 'SUCCESS', error: null };
    
    const matchCount = await this.syncFixturesAndEvents();
    result.matches = matchCount;
    
    const { oddsCount, changesCount } = await this.syncOdds();
    result.odds = oddsCount;
    result.changes = changesCount;
    
    // After syncing, compute team stats and H2H
    await this.computeTeamStats();
    await this.computeH2HRecords();
    
    return result;
  }

  // ============================================
  // 1. Sync Fixtures, Events & Match Stats
  // ============================================
  private async syncFixturesAndEvents(): Promise<number> {
    this.logger.log('Fetching Fixtures & Events from API-Football...');
    let fixtures = [];
    try {
      const resp = await axios.get(`${this.API_FOOTBALL_URL}/fixtures`, {
        headers: { 'x-apisports-key': this.API_FOOTBALL_KEY },
        params: { league: this.WC_LEAGUE_ID, season: this.SEASON },
      });
      fixtures = resp.data?.response || [];
    } catch (e) {
      this.logger.error('API-Football sync failed: ' + e.message);
    }

    this.logger.log(`Found ${fixtures.length} matches from API-Football.`);

    const tournament = await this.prisma.tournament.upsert({
      where: { name: 'World Cup 2026' },
      update: {},
      create: { name: 'World Cup 2026', country: 'USA/Canada/Mexico' },
    });

    for (const item of fixtures) {
      const homeTeam = await this.prisma.team.upsert({
        where: { name: item.teams.home.name },
        update: { logo: item.teams.home.logo },
        create: { name: item.teams.home.name, logo: item.teams.home.logo },
      });

      const awayTeam = await this.prisma.team.upsert({
        where: { name: item.teams.away.name },
        update: { logo: item.teams.away.logo },
        create: { name: item.teams.away.name, logo: item.teams.away.logo },
      });

      // Extract Cards from events
      let homeRedCards = 0;
      let awayRedCards = 0;
      const events = item.events || [];

      for (const ev of events) {
        if (ev.type === 'Card' && ev.detail === 'Red Card') {
          if (ev.team.id === item.teams.home.id) homeRedCards++;
          if (ev.team.id === item.teams.away.id) awayRedCards++;
        }
      }

      const match = await this.prisma.match.upsert({
        where: { externalId: item.fixture.id.toString() },
        update: {
          startTime: new Date(item.fixture.date),
          status: item.fixture.status.short,
          homeScore: item.goals.home ?? 0,
          awayScore: item.goals.away ?? 0,
          homeRedCards,
          awayRedCards,
        },
        create: {
          externalId: item.fixture.id.toString(),
          tournamentId: tournament.id,
          homeTeamId: homeTeam.id,
          awayTeamId: awayTeam.id,
          startTime: new Date(item.fixture.date),
          status: item.fixture.status.short,
          homeScore: item.goals.home ?? 0,
          awayScore: item.goals.away ?? 0,
          homeRedCards,
          awayRedCards,
        },
      });

      // Store individual events (Goals, Red Cards, Yellow Cards)
      // First delete old events to avoid duplicates, then re-insert
      if (events.length > 0) {
        await this.prisma.matchEvent.deleteMany({ where: { matchId: match.id } });
        
        for (const ev of events) {
          if (ev.type === 'Card' || ev.type === 'Goal') {
            const teamId = ev.team.id === item.teams.home.id ? homeTeam.id : awayTeam.id;
            
            // Map event type to our standard types
            let eventType = ev.type;
            if (ev.type === 'Card') {
              eventType = ev.detail === 'Red Card' ? 'RED_CARD' : 'YELLOW_CARD';
            } else if (ev.type === 'Goal') {
              eventType = 'GOAL';
            }
            
            await this.prisma.matchEvent.create({
              data: {
                matchId: match.id,
                teamId: teamId,
                type: eventType,
                minute: ev.time.elapsed ?? 0,
                player: ev.player?.name || 'Unknown',
              }
            });
          }
        }
      }

      // Sync Match Statistics (possession, shots, fouls, corners, cards)
      await this.syncMatchStats(item.fixture.id, match.id);
    }

    return fixtures.length;
  }

  // ============================================
  // 1b. Sync Match Statistics from API-Football
  // ============================================
  private async syncMatchStats(fixtureId: number, matchId: number) {
    try {
      const resp = await axios.get(`${this.API_FOOTBALL_URL}/fixtures/statistics`, {
        headers: { 'x-apisports-key': this.API_FOOTBALL_KEY },
        params: { fixture: fixtureId },
      });

      const statsData = resp.data?.response || [];
      if (statsData.length < 2) return; // Need both teams' stats

      const homeStats = statsData[0]?.statistics || [];
      const awayStats = statsData[1]?.statistics || [];

      const getStat = (stats: any[], type: string): any => {
        const stat = stats.find((s: any) => s.type === type);
        return stat?.value ?? null;
      };

      const parsePossession = (val: any): number | null => {
        if (val === null || val === undefined) return null;
        return parseFloat(String(val).replace('%', ''));
      };

      await this.prisma.matchStats.upsert({
        where: { matchId },
        update: {
          homePossession: parsePossession(getStat(homeStats, 'Ball Possession')),
          awayPossession: parsePossession(getStat(awayStats, 'Ball Possession')),
          homeShots: getStat(homeStats, 'Total Shots'),
          awayShots: getStat(awayStats, 'Total Shots'),
          homeShotsOnTarget: getStat(homeStats, 'Shots on Goal'),
          awayShotsOnTarget: getStat(awayStats, 'Shots on Goal'),
          homeYellowCards: getStat(homeStats, 'Yellow Cards') ?? 0,
          awayYellowCards: getStat(awayStats, 'Yellow Cards') ?? 0,
          homeCorners: getStat(homeStats, 'Corner Kicks') ?? 0,
          awayCorners: getStat(awayStats, 'Corner Kicks') ?? 0,
          homeFouls: getStat(homeStats, 'Fouls'),
          awayFouls: getStat(awayStats, 'Fouls'),
          homeXG: getStat(homeStats, 'expected_goals') ? parseFloat(getStat(homeStats, 'expected_goals')) : null,
          awayXG: getStat(awayStats, 'expected_goals') ? parseFloat(getStat(awayStats, 'expected_goals')) : null,
        },
        create: {
          matchId,
          homePossession: parsePossession(getStat(homeStats, 'Ball Possession')),
          awayPossession: parsePossession(getStat(awayStats, 'Ball Possession')),
          homeShots: getStat(homeStats, 'Total Shots'),
          awayShots: getStat(awayStats, 'Total Shots'),
          homeShotsOnTarget: getStat(homeStats, 'Shots on Goal'),
          awayShotsOnTarget: getStat(awayStats, 'Shots on Goal'),
          homeYellowCards: getStat(homeStats, 'Yellow Cards') ?? 0,
          awayYellowCards: getStat(awayStats, 'Yellow Cards') ?? 0,
          homeCorners: getStat(homeStats, 'Corner Kicks') ?? 0,
          awayCorners: getStat(awayStats, 'Corner Kicks') ?? 0,
          homeFouls: getStat(homeStats, 'Fouls'),
          awayFouls: getStat(awayStats, 'Fouls'),
          homeXG: getStat(homeStats, 'expected_goals') ? parseFloat(getStat(homeStats, 'expected_goals')) : null,
          awayXG: getStat(awayStats, 'expected_goals') ? parseFloat(getStat(awayStats, 'expected_goals')) : null,
        },
      });

      // Also update corners on Match table
      await this.prisma.match.update({
        where: { id: matchId },
        data: {
          homeCorners: getStat(homeStats, 'Corner Kicks') ?? 0,
          awayCorners: getStat(awayStats, 'Corner Kicks') ?? 0,
        }
      });
    } catch (e) {
      // Statistics may not be available for unplayed matches - this is normal
      if (!e.message?.includes('404')) {
        this.logger.debug(`Stats not available for fixture ${fixtureId}: ${e.message}`);
      }
    }
  }

  // ============================================
  // 2. Sync Odds with Opening Odds tracking
  // ============================================
  private async syncOdds(): Promise<{ oddsCount: number; changesCount: number }> {
    this.logger.log('Fetching Odds from The Odds API...');
    let oddsCount = 0;
    let changesCount = 0;

    try {
      const resp = await axios.get(`${this.THE_ODDS_API_URL}/${this.SPORT_KEY}/odds/`, {
        params: {
          apiKey: this.THE_ODDS_API_KEY,
          regions: 'eu', // Europe bookmakers like Pinnacle
          markets: 'h2h,spreads,totals',
          oddsFormat: 'decimal',
        },
      });

      const oddsData = resp.data || [];
      this.logger.log(`Found odds for ${oddsData.length} matches from The Odds API.`);

      for (const oddsMatch of oddsData) {
        const match = await this.matchResolver(oddsMatch.home_team, oddsMatch.away_team, new Date(oddsMatch.commence_time));
        if (!match) continue;

        for (const bookmaker of oddsMatch.bookmakers) {
          for (const market of bookmaker.markets) {
            
            let homeWin: number | undefined, draw: number | undefined, awayWin: number | undefined;
            let over: number | undefined, under: number | undefined, handicap: string | undefined;
            
            if (market.key === 'h2h') {
              homeWin = market.outcomes.find((o: any) => o.name === oddsMatch.home_team)?.price;
              awayWin = market.outcomes.find((o: any) => o.name === oddsMatch.away_team)?.price;
              draw = market.outcomes.find((o: any) => o.name === 'Draw')?.price;
            } else if (market.key === 'totals') {
              over = market.outcomes.find((o: any) => o.name === 'Over')?.price;
              under = market.outcomes.find((o: any) => o.name === 'Under')?.price;
              handicap = market.outcomes[0]?.point?.toString();
            } else if (market.key === 'spreads') {
              handicap = market.outcomes.find((o: any) => o.name === oddsMatch.home_team)?.point?.toString();
            }

            if (homeWin || draw || awayWin || over || handicap) {
              // Check for existing odds record
              const existingOdds = await this.prisma.odds.findUnique({
                where: {
                  matchId_bookmaker_type_handicap: {
                    matchId: match.id,
                    bookmaker: bookmaker.title,
                    type: market.key,
                    handicap: handicap || '',
                  }
                }
              });

              let shouldCreateHistory = false;
              if (existingOdds) {
                if (
                  existingOdds.homeWin !== (homeWin ?? null) ||
                  existingOdds.draw !== (draw ?? null) ||
                  existingOdds.awayWin !== (awayWin ?? null) ||
                  existingOdds.over !== (over ?? null) ||
                  existingOdds.under !== (under ?? null)
                ) {
                  shouldCreateHistory = true;
                  changesCount++;
                }
              }

              // Upsert Odds - preserve opening odds
              await this.prisma.odds.upsert({
                where: {
                  matchId_bookmaker_type_handicap: {
                    matchId: match.id,
                    bookmaker: bookmaker.title,
                    type: market.key,
                    handicap: handicap || '',
                  }
                },
                update: { homeWin, draw, awayWin, over, under },
                create: {
                  matchId: match.id,
                  bookmaker: bookmaker.title,
                  type: market.key,
                  handicap: handicap || '',
                  homeWin, draw, awayWin, over, under,
                  // First time = this IS the opening odds
                  openingHomeWin: homeWin,
                  openingDraw: draw,
                  openingAwayWin: awayWin,
                  openingOver: over,
                  openingUnder: under,
                  isOpeningSet: true,
                }
              });

              oddsCount++;

              // Save OddsHistory if changed
              if (shouldCreateHistory && existingOdds) {
                await this.prisma.oddsHistory.create({
                  data: {
                    matchId: match.id,
                    bookmaker: bookmaker.title,
                    type: market.key,
                    handicap: handicap || '',
                    oldHomeWin: existingOdds.homeWin,
                    oldDraw: existingOdds.draw,
                    oldAwayWin: existingOdds.awayWin,
                    oldOver: existingOdds.over,
                    oldUnder: existingOdds.under,
                    newHomeWin: homeWin,
                    newDraw: draw,
                    newAwayWin: awayWin,
                    newOver: over,
                    newUnder: under,
                  }
                });
                this.logger.debug(`Saved OddsHistory for Match ${match.id} - ${bookmaker.title}`);
              }
            }
          }
        }
      }
    } catch (e) {
      this.logger.error('Failed to sync The Odds API: ' + e.message);
    }

    this.logger.log(`Odds sync complete: ${oddsCount} odds processed, ${changesCount} changes detected.`);
    return { oddsCount, changesCount };
  }

  // ============================================
  // 3. Compute Team Statistics (from Match data)
  // ============================================
  private async computeTeamStats() {
    this.logger.log('Computing Team Statistics...');
    const teams = await this.prisma.team.findMany();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    for (const team of teams) {
      // Get all finished matches for this team, ordered by date desc
      const matches = await this.prisma.match.findMany({
        where: {
          status: 'FT',
          OR: [
            { homeTeamId: team.id },
            { awayTeamId: team.id },
          ],
        },
        include: { matchStats: true },
        orderBy: { startTime: 'desc' },
      });

      if (matches.length === 0) continue;

      // Compute form
      const last5 = matches.slice(0, 5);
      const last10 = matches.slice(0, 10);

      const getResult = (m: any, teamId: number): string => {
        const isHome = m.homeTeamId === teamId;
        const goalsFor = isHome ? m.homeScore : m.awayScore;
        const goalsAgainst = isHome ? m.awayScore : m.homeScore;
        if (goalsFor > goalsAgainst) return 'W';
        if (goalsFor < goalsAgainst) return 'L';
        return 'D';
      };

      const formString = (ms: any[]) => ms.map(m => getResult(m, team.id)).join('');
      const formPoints = (ms: any[]) => {
        if (ms.length === 0) return 0;
        const total = ms.reduce((sum, m) => {
          const r = getResult(m, team.id);
          return sum + (r === 'W' ? 3 : r === 'D' ? 1 : 0);
        }, 0);
        return total / ms.length;
      };

      // Goal stats
      const avgGoals = (ms: any[], type: 'scored' | 'conceded') => {
        if (ms.length === 0) return 0;
        const total = ms.reduce((sum, m) => {
          const isHome = m.homeTeamId === team.id;
          if (type === 'scored') return sum + (isHome ? m.homeScore : m.awayScore);
          return sum + (isHome ? m.awayScore : m.homeScore);
        }, 0);
        return total / ms.length;
      };

      // Home/Away specific
      const homeMatches = matches.filter(m => m.homeTeamId === team.id);
      const awayMatches = matches.filter(m => m.awayTeamId === team.id);
      
      const homeWins = homeMatches.filter(m => m.homeScore > m.awayScore).length;
      const awayWins = awayMatches.filter(m => m.awayScore > m.homeScore).length;
      
      const homeWinRate = homeMatches.length > 0 ? homeWins / homeMatches.length : null;
      const awayWinRate = awayMatches.length > 0 ? awayWins / awayMatches.length : null;
      
      const homeAvgGoals = homeMatches.length > 0 
        ? homeMatches.reduce((s, m) => s + m.homeScore, 0) / homeMatches.length : null;
      const awayAvgGoals = awayMatches.length > 0 
        ? awayMatches.reduce((s, m) => s + m.awayScore, 0) / awayMatches.length : null;

      // Discipline & Advanced stats (from MatchStats)
      const matchesWithStats = matches.filter(m => m.matchStats);
      let avgYellowCards: number | null = null;
      let avgCorners: number | null = null;
      let avgFouls: number | null = null;
      let avgPossession: number | null = null;
      let avgShots: number | null = null;
      let avgShotsOnTarget: number | null = null;

      if (matchesWithStats.length > 0) {
        const statsAgg = matchesWithStats.reduce((acc, m) => {
          const ms = m.matchStats!;
          const isHome = m.homeTeamId === team.id;
          acc.yellowCards += isHome ? (ms.homeYellowCards ?? 0) : (ms.awayYellowCards ?? 0);
          acc.corners += isHome ? (ms.homeCorners ?? 0) : (ms.awayCorners ?? 0);
          acc.fouls += isHome ? (ms.homeFouls ?? 0) : (ms.awayFouls ?? 0);
          acc.possession += isHome ? (ms.homePossession ?? 0) : (ms.awayPossession ?? 0);
          acc.shots += isHome ? (ms.homeShots ?? 0) : (ms.awayShots ?? 0);
          acc.shotsOnTarget += isHome ? (ms.homeShotsOnTarget ?? 0) : (ms.awayShotsOnTarget ?? 0);
          return acc;
        }, { yellowCards: 0, corners: 0, fouls: 0, possession: 0, shots: 0, shotsOnTarget: 0 });

        const n = matchesWithStats.length;
        avgYellowCards = statsAgg.yellowCards / n;
        avgCorners = statsAgg.corners / n;
        avgFouls = statsAgg.fouls / n;
        avgPossession = statsAgg.possession / n;
        avgShots = statsAgg.shots / n;
        avgShotsOnTarget = statsAgg.shotsOnTarget / n;
      }

      // Clean sheet & BTTS rates
      const cleanSheets = matches.filter(m => {
        const isHome = m.homeTeamId === team.id;
        return isHome ? m.awayScore === 0 : m.homeScore === 0;
      }).length;
      const bttsMatches = matches.filter(m => m.homeScore > 0 && m.awayScore > 0).length;

      await this.prisma.teamStats.upsert({
        where: { teamId_snapshotDate: { teamId: team.id, snapshotDate: today } },
        update: {
          formLast5: formString(last5),
          formLast10: formString(last10),
          formPoints5: formPoints(last5),
          formPoints10: formPoints(last10),
          avgGoalsScored5: avgGoals(last5, 'scored'),
          avgGoalsConceded5: avgGoals(last5, 'conceded'),
          avgGoalsScored10: avgGoals(last10, 'scored'),
          avgGoalsConceded10: avgGoals(last10, 'conceded'),
          homeWinRate,
          awayWinRate,
          homeAvgGoals,
          awayAvgGoals,
          avgYellowCards,
          avgCorners,
          avgFouls,
          avgPossession,
          avgShots,
          avgShotsOnTarget,
          cleanSheetRate: matches.length > 0 ? cleanSheets / matches.length : null,
          bttsRate: matches.length > 0 ? bttsMatches / matches.length : null,
        },
        create: {
          teamId: team.id,
          snapshotDate: today,
          formLast5: formString(last5),
          formLast10: formString(last10),
          formPoints5: formPoints(last5),
          formPoints10: formPoints(last10),
          avgGoalsScored5: avgGoals(last5, 'scored'),
          avgGoalsConceded5: avgGoals(last5, 'conceded'),
          avgGoalsScored10: avgGoals(last10, 'scored'),
          avgGoalsConceded10: avgGoals(last10, 'conceded'),
          homeWinRate,
          awayWinRate,
          homeAvgGoals,
          awayAvgGoals,
          avgYellowCards,
          avgCorners,
          avgFouls,
          avgPossession,
          avgShots,
          avgShotsOnTarget,
          cleanSheetRate: matches.length > 0 ? cleanSheets / matches.length : null,
          bttsRate: matches.length > 0 ? bttsMatches / matches.length : null,
        },
      });
    }

    this.logger.log(`Team statistics computed for ${teams.length} teams.`);
  }

  // ============================================
  // 4. Compute Head-to-Head Records
  // ============================================
  private async computeH2HRecords() {
    this.logger.log('Computing H2H Records...');
    
    // Get all unique team pairs from finished matches
    const finishedMatches = await this.prisma.match.findMany({
      where: { status: 'FT' },
      orderBy: { startTime: 'desc' },
    });

    const pairsSeen = new Set<string>();
    
    for (const match of finishedMatches) {
      // Normalize pair: smaller ID first
      const t1 = Math.min(match.homeTeamId, match.awayTeamId);
      const t2 = Math.max(match.homeTeamId, match.awayTeamId);
      const pairKey = `${t1}-${t2}`;
      
      if (pairsSeen.has(pairKey)) continue;
      pairsSeen.add(pairKey);

      // Get all matches between these two teams
      const h2hMatches = finishedMatches.filter(m =>
        (m.homeTeamId === t1 && m.awayTeamId === t2) ||
        (m.homeTeamId === t2 && m.awayTeamId === t1)
      );

      let team1Wins = 0, team2Wins = 0, draws = 0, team1Goals = 0, team2Goals = 0;

      for (const m of h2hMatches) {
        const t1Goals = m.homeTeamId === t1 ? m.homeScore : m.awayScore;
        const t2Goals = m.homeTeamId === t1 ? m.awayScore : m.homeScore;
        team1Goals += t1Goals;
        team2Goals += t2Goals;
        if (t1Goals > t2Goals) team1Wins++;
        else if (t1Goals < t2Goals) team2Wins++;
        else draws++;
      }

      const last5 = h2hMatches.slice(0, 5);
      const last5Data = last5.map(m => ({
        date: m.startTime,
        homeTeamId: m.homeTeamId,
        awayTeamId: m.awayTeamId,
        homeScore: m.homeScore,
        awayScore: m.awayScore,
      }));

      const last5T1Goals = last5.reduce((s, m) => 
        s + (m.homeTeamId === t1 ? m.homeScore : m.awayScore), 0);
      const last5T2Goals = last5.reduce((s, m) => 
        s + (m.homeTeamId === t1 ? m.awayScore : m.homeScore), 0);

      await this.prisma.h2HRecord.upsert({
        where: { team1Id_team2Id: { team1Id: t1, team2Id: t2 } },
        update: {
          totalMatches: h2hMatches.length,
          team1Wins,
          team2Wins,
          draws,
          team1Goals,
          team2Goals,
          last5Matches: JSON.stringify(last5Data),
          last5Team1Goals: last5T1Goals,
          last5Team2Goals: last5T2Goals,
        },
        create: {
          team1Id: t1,
          team2Id: t2,
          totalMatches: h2hMatches.length,
          team1Wins,
          team2Wins,
          draws,
          team1Goals,
          team2Goals,
          last5Matches: JSON.stringify(last5Data),
          last5Team1Goals: last5T1Goals,
          last5Team2Goals: last5T2Goals,
        },
      });
    }

    this.logger.log(`H2H records computed for ${pairsSeen.size} team pairs.`);
  }

  // ============================================
  // Helper: Match resolver between APIs
  // ============================================
  private async matchResolver(homeTeamName: string, awayTeamName: string, commenceTime: Date) {
    // 1. Try matching by team name prefix
    let match = await this.prisma.match.findFirst({
      where: {
        homeTeam: { name: { contains: homeTeamName.split(' ')[0] } },
        awayTeam: { name: { contains: awayTeamName.split(' ')[0] } },
      }
    });

    // 2. Fallback: Create from The Odds API data
    if (!match) {
      const tournament = await this.prisma.tournament.upsert({
        where: { name: 'World Cup 2026' },
        update: {},
        create: { name: 'World Cup 2026', country: 'USA/Canada/Mexico' },
      });

      const homeTeam = await this.prisma.team.upsert({
        where: { name: homeTeamName },
        update: {},
        create: { name: homeTeamName },
      });

      const awayTeam = await this.prisma.team.upsert({
        where: { name: awayTeamName },
        update: {},
        create: { name: awayTeamName },
      });

      const externalId = `oddsapi_${homeTeamName}_${awayTeamName}_${commenceTime.getTime()}`;

      match = await this.prisma.match.create({
        data: {
          externalId,
          tournamentId: tournament.id,
          homeTeamId: homeTeam.id,
          awayTeamId: awayTeam.id,
          startTime: commenceTime,
          status: 'NS',
        }
      });
      this.logger.log(`Created fallback match: ${homeTeamName} vs ${awayTeamName}`);
    }

    return match;
  }
}
