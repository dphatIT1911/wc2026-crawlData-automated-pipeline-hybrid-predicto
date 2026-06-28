require('dotenv').config();
const { Pool } = require('pg');
const { PrismaPg } = require('@prisma/adapter-pg');
const { PrismaClient } = require('@prisma/client');
const fs = require('fs');

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const adapter = new PrismaPg(pool);
const prisma = new PrismaClient({ adapter });

async function importMatches() {
  console.log('--- Đang Import Dữ Liệu Lịch Sử ---');

  // Find or create default tournament
  let tournament = await prisma.tournament.findFirst({ where: { name: "Historical Matches" } });
  if (!tournament) {
      tournament = await prisma.tournament.create({
          data: { name: "Historical Matches", country: "International" }
      });
  }

  const rawData = fs.readFileSync('prediction-engine/historical_matches.json');
  const matches = JSON.parse(rawData);
  console.log(`Tìm thấy ${matches.length} trận đấu trong file JSON.`);

  let imported = 0;
  for (const match of matches) {
    try {
      // 1. Tìm hoặc tạo Home Team
      let homeTeam = await prisma.team.findFirst({ where: { name: match.homeTeam } });
      if (!homeTeam) {
        homeTeam = await prisma.team.create({
          data: { name: match.homeTeam, code: match.homeTeam.substring(0, 3).toUpperCase() }
        });
      }

      // 2. Tìm hoặc tạo Away Team
      let awayTeam = await prisma.team.findFirst({ where: { name: match.awayTeam } });
      if (!awayTeam) {
        awayTeam = await prisma.team.create({
          data: { name: match.awayTeam, code: match.awayTeam.substring(0, 3).toUpperCase() }
        });
      }

      let rawStartTime = match.startTime;
      if (rawStartTime.includes('.000.000Z')) {
          rawStartTime = rawStartTime.replace('.000.000Z', '.000Z');
      }
      let parsedDate = new Date(rawStartTime);
      if (isNaN(parsedDate.getTime())) {
          parsedDate = new Date(); // fallback
      }

      // 3. Upsert Match
      const dbMatch = await prisma.match.upsert({
        where: { externalId: match.externalId },
        update: {
            homeScore: match.homeScore,
            awayScore: match.awayScore,
            status: "FT"
        },
        create: {
          tournamentId: tournament.id,
          homeTeamId: homeTeam.id,
          awayTeamId: awayTeam.id,
          homeScore: match.homeScore,
          awayScore: match.awayScore,
          startTime: parsedDate,
          status: 'FT',
          externalId: match.externalId
        }
      });

      const statsMapping = {
          homePossession: match.stats.possessionHome,
          awayPossession: match.stats.possessionAway,
          homeShotsOnTarget: match.stats.shotsOnTargetHome,
          awayShotsOnTarget: match.stats.shotsOnTargetAway,
          homeCorners: match.stats.cornersHome,
          awayCorners: match.stats.cornersAway,
          homeFouls: match.stats.foulsHome,
          awayFouls: match.stats.foulsAway,
          homeYellowCards: match.stats.yellowCardsHome,
          awayYellowCards: match.stats.yellowCardsAway,
      };

      // 4. Upsert MatchStats
      await prisma.matchStats.upsert({
        where: { matchId: dbMatch.id },
        update: statsMapping,
        create: {
          matchId: dbMatch.id,
          ...statsMapping
        }
      });
      
      imported++;
      if (imported % 10 === 0) {
        console.log(`Đã import ${imported}/${matches.length} trận đấu...`);
      }
    } catch (e) {
      console.error(`Lỗi khi import trận ${match.homeTeam} vs ${match.awayTeam}:`, e.message);
    }
  }

  console.log(`\nHoàn tất! Đã import thành công ${imported} trận đấu lịch sử vào Database.`);
  await prisma.$disconnect();
}

importMatches().catch(e => {
  console.error(e);
  process.exit(1);
});
