import { Controller, Get } from '@nestjs/common';
import { CrawlerService } from './crawler.service';

@Controller('crawler')
export class CrawlerController {
  constructor(private readonly crawlerService: CrawlerService) {}

  @Get('run')
  async runCrawlerManually() {
    try {
      await this.crawlerService.crawlMatchesAndOdds();
      return { message: 'Crawler completed successfully.' };
    } catch (error) {
      return { message: 'Internal Server Error', error: error.message, stack: error.stack };
    }
  }
}
