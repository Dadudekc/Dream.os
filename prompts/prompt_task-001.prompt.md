# Service Class Generator
Generate a AuthService service class

## Description
Create a service class for handling authentication and authorization that follows best practices for dependency injection, error handling, and testability.

## Requirements
- Create a well-structured service class with proper error handling
- Implement dependency injection for testability
- Add comprehensive logging
- Include JSDoc or typings for all methods and parameters
- Ensure proper error handling

## Dependencies
DatabaseService
TokenManager

## Example Output
```typescript
import { Injectable } from '@nestjs/common';
import { Logger } from '../utils/logger';

@Injectable()
export class ExampleService {
  private logger = new Logger(ExampleService.name);
  
  constructor(
    private readonly configService: ConfigService,
  ) {}
  
  async processData(data: any): Promise<Result> {
    try {
      this.logger.info('Processing data', { dataId: data.id });
      // Implementation here
      return { success: true, data: result };
    } catch (error) {
      this.logger.error('Failed to process data', { error, dataId: data?.id });
      throw new ServiceException('Failed to process data', error);
    }
  }
} 