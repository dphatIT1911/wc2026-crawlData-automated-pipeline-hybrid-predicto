const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  console.log('Match count:', await prisma.match.count());
  console.log('MatchEvent count:', await prisma.matchEvent.count());
  console.log('Odds count:', await prisma.odds.count());
  console.log('OddsHistory count:', await prisma.oddsHistory.count());
  console.log('Team count:', await prisma.team.count());
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
