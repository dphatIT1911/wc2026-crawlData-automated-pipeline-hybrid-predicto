import 'dotenv/config';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  
  // Enable CORS for frontend
  app.enableCors({
    origin: process.env.FRONTEND_URL ? process.env.FRONTEND_URL.split(',') : true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    credentials: true,
  });
  
  // Bind to 0.0.0.0 to allow external connections on Render
  await app.listen(process.env.PORT ?? 3000, '0.0.0.0');
}
bootstrap();
