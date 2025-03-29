# Changelog

## [Unreleased]

### Added
- Hybrid context system for enhanced Dreamscape Episodes
  - New `PromptContextSynthesizer` class that combines multiple context sources
  - Context quality metrics and confidence scoring
  - Configurable weighting system for different context sources
  - Improved memory management with automatic conflict resolution
  - Enhanced episode chain tracking with better narrative continuity

### Changed
- Updated `DreamscapeGenerationService` to use context synthesizer
- Improved `ServiceInitializer` with better dependency management
- Enhanced UI to display context confidence and source information

### Fixed
- Resolved inconsistencies in episode generation with better context handling
- Fixed issues with episode chaining by adding structured memory updates

## [1.0.0] - 2023-05-15 