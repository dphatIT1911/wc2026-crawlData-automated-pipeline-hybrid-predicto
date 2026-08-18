import { Injectable } from '@nestjs/common';
import { PrismaService } from './prisma.service';

@Injectable()
export class SettingsService {
  constructor(private prisma: PrismaService) {}

  async getSettings() {
    const settings = await this.prisma.systemSetting.findMany();
    const result: Record<string, string> = {};
    settings.forEach(s => result[s.key] = s.value);
    return result;
  }

  async updateSettings(updates: Record<string, string>) {
    const promises = Object.keys(updates).map(key => 
      this.prisma.systemSetting.upsert({
        where: { key },
        update: { value: updates[key] },
        create: { key, value: updates[key] }
      })
    );
    await Promise.all(promises);
    return this.getSettings();
  }
}
