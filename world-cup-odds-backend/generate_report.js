const { PrismaClient } = require('@prisma/client');
const { Pool } = require('pg');
const { PrismaPg } = require('@prisma/adapter-pg');
const fs = require('fs');
require('dotenv').config();

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const adapter = new PrismaPg(pool);
const prisma = new PrismaClient({ adapter });

async function generateReport() {
  let md = '# Báo cáo Chi tiết Dữ liệu Hệ thống\n\n';

  const tables = [
    { name: 'Tournament', model: prisma.tournament },
    { name: 'Team', model: prisma.team },
    { name: 'Match', model: prisma.match },
    { name: 'MatchEvent', model: prisma.matchEvent },
    { name: 'Odds', model: prisma.odds },
    { name: 'OddsHistory', model: prisma.oddsHistory },
    { name: 'CrawlerLog', model: prisma.crawlerLog },
  ];

  for (const table of tables) {
    md += `## Bảng: ${table.name}\n\n`;
    const records = await table.model.findMany({ take: 5 });
    
    if (records.length === 0) {
      md += `*Hiện tại bảng này chưa có dữ liệu.*\n\n`;
      continue;
    }

    // Get all columns from the first record
    const columns = Object.keys(records[0]);
    
    // Create Markdown Table Header
    md += `| ` + columns.join(' | ') + ` |\n`;
    md += `| ` + columns.map(() => '---').join(' | ') + ` |\n`;

    // Add 5 rows of data
    for (const record of records) {
      const row = columns.map(col => {
        let val = record[col];
        if (val === null || val === undefined) return 'NULL';
        if (val instanceof Date) return val.toISOString();
        if (typeof val === 'object') return JSON.stringify(val);
        return String(val);
      });
      md += `| ` + row.join(' | ') + ` |\n`;
    }
    md += '\n---\n\n';
  }

  // Write to artifacts directory
  fs.writeFileSync('C:\\Users\\Admin\\.gemini\\antigravity-ide\\brain\\fe48862b-7633-42ce-b04f-a7f4716ce64f\\database_report.md', md);
  console.log('Report generated successfully.');
}

generateReport()
  .catch(e => console.error(e))
  .finally(() => prisma.$disconnect());
