const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function checkData() {
  console.log('--- Kiểm Tra Cơ Sở Dữ Liệu ---');
  
  const matches = await prisma.match.count();
  const odds = await prisma.odds.count();
  const oddsHistory = await prisma.oddsHistory.count();
  const matchStats = await prisma.matchStats.count();
  const teamStats = await prisma.teamStats.count();
  const h2h = await prisma.h2HRecord.count();
  const events = await prisma.matchEvent.count();

  console.log(`Số trận đấu (Match): ${matches}`);
  console.log(`Số tỷ lệ cược (Odds): ${odds}`);
  console.log(`Lịch sử biến động tỷ lệ (OddsHistory): ${oddsHistory}`);
  console.log(`Thống kê trận đấu (MatchStats): ${matchStats}`);
  console.log(`Thống kê đội bóng (TeamStats): ${teamStats}`);
  console.log(`Lịch sử đối đầu (H2HRecord): ${h2h}`);
  console.log(`Sự kiện trận đấu (MatchEvent): ${events}`);

  await prisma.$disconnect();
}

checkData().catch(e => {
  console.error(e);
  process.exit(1);
});
