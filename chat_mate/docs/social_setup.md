# Social Platform Setup

## Overview
The social platform setup functionality provides a unified interface for managing connections to various social media platforms. It replaces the separate Discord and Social Dashboard tabs with a streamlined wizard-style setup process.

## Architecture

### Components

1. **SocialSetupTab**
   - Main UI component that provides the wizard interface
   - Manages platform selection, credential input, and connection status
   - Integrates with the configuration system for credential storage

2. **SocialLoginManager**
   - Core service that orchestrates platform-specific login services
   - Manages service lifecycle and connection states
   - Provides a unified interface for platform operations

3. **BasePlatformLoginService**
   - Abstract base class defining the interface for platform-specific login services
   - Handles common functionality like connection state management and logging
   - Provides hooks for platform-specific implementations

4. **Platform-Specific Services**
   - Concrete implementations of BasePlatformLoginService
   - Handle platform-specific authentication flows
   - Currently implemented:
     - DiscordLoginService
   - Planned implementations:
     - TwitterLoginService
     - FacebookLoginService
     - InstagramLoginService
     - RedditLoginService
     - StocktwitsLoginService
     - LinkedInLoginService

## Features

### Wizard Interface
- Step-by-step platform setup process
- Platform selection with checkboxes
- Dynamic credential form based on selected platform
- Connection status monitoring
- Secure credential storage (optional)

### Platform Support
- Discord integration with both token and credential-based authentication
- Extensible architecture for adding new platforms
- Unified status monitoring across all platforms

### Security
- Optional secure credential storage
- Password fields properly masked
- Token-based authentication support where available
- Session management with proper cleanup

### Configuration
- Persistent storage of platform selections
- Secure credential storage (when enabled)
- Auto-reconnect settings
- Platform-specific advanced settings

## Usage

### Basic Setup
1. Navigate to the "Social Setup" tab
2. Select desired platforms
3. Configure each platform's credentials
4. Review and confirm settings

### Advanced Features
- Toggle "Save credentials securely" for persistent storage
- Enable "Auto-reconnect on startup" for automatic session restoration
- Access platform-specific advanced settings
- Monitor connection status for all platforms

### Development

#### Adding a New Platform
1. Create a new service class extending `BasePlatformLoginService`
2. Implement required abstract methods:
   - `platform_name`
   - `connect`
   - `disconnect`
   - `test_connection`
   - `get_connection_status`
3. Register the service in `SocialLoginManager`
4. Add platform-specific UI fields in `SocialSetupTab`

#### Testing
- Comprehensive test suite in `test_social_setup_tab.py`
- Tests cover:
  - Component initialization
  - Platform selection
  - Navigation
  - Credential management
  - Error handling
  - Connection status updates

## Dependencies
- PyQt5 for UI components
- Selenium WebDriver for platform automation
- ConfigManager for credential storage
- LoggingService for operation logging

## Future Enhancements
1. Additional platform implementations
2. OAuth integration for supported platforms
3. Bulk platform setup
4. Connection health monitoring
5. Automated retry mechanisms
6. Enhanced security features
7. Platform-specific analytics 