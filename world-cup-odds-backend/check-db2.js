const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function checkData() {
  console.log('--- Checking Database ---');
  
  const matches = await prisma.match.findMany({ include: { matchStats: true, odds: true } });
  console.log(`Total Matches: ${matches.length}`);
  if (matches.length > 0) {
    console.log('Sample Match 1:', matches[0].externalId, matches[0].status);
    console.log('Match Stats:', matches[0].matchStats ? 'Yes' : 'No', matches[0].matchStats);
    console.log('Odds Count:', matches[0].odds.length);
  }

  const teamStats = await prisma.teamStats.findMany();
  console.log(`\nTotal TeamStats: ${teamStats.length}`);
  if (teamStats.length > 0) {
    console.log('Sample TeamStats:', teamStats[0]);
  }

  const h2h = await prisma.h2HRecord.findMany();
  console.log(`\nTotal H2HRecords: ${h2h.length}`);
  if (h2h.length > 0) {
    console.log('Sample H2HRecord:', h2h[0]);
  }

  const odds = await prisma.odds.findMany({ take: 5 });
  console.log(`\nSample Odds:`, odds);

  const oddsHistory = await prisma.oddsHistory.findMany({ take: 5 });
  console.log(`\nSample OddsHistory:`, oddsHistory);

  const crawlerLogs = await prisma.crawlerLog.findMany({ orderBy: { runAt: 'desc' }, take: 1 });
  console.log(`\nLatest Crawler Log:`, crawlerLogs[0]);

  await prisma.$disconnect();
}

checkData().catch(e => {
  console.error(e);
  process.exit(1);
});
